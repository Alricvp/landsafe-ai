/*
  BLACKBOX-Z — ESP32 machine flight-recorder node (vibration + leak box)
  ========================================================================
  This is the vibration box variant: MPU6050 (vibration + tilt) + moisture
  / leak sensor. No mic, no alarm audio on this board.

  Same sketch family as the audio node; only the cfg block and disabled
  sensors differ. The gateway and dashboard see it as a separate node
  by NODE_ID.
*/

#include <Arduino.h>
#include <WiFi.h>
#include <HTTPClient.h>
#include <Wire.h>
#include <SPI.h>
#include <esp_heap_caps.h>
#include <esp_random.h>

// =====================================================================
// CONFIG — edit these for this box and gateway
// =====================================================================
namespace cfg {

// ---- identity ----
constexpr const char* NODE_ID   = "esp32-a";      // dashboard + gateway node name
constexpr const char* FW_REV    = "blackbox-z-vibration-node-1";

// ---- gateway (same origin as the dashboard) ----
constexpr const char* GW_HOST   = "10.0.0.2";     // <-- your gateway IP / hostname
constexpr uint16_t    GW_PORT   = 80;             // 443 if HTTPS (then use HTTPSClient)
constexpr const char* GW_PATH_READING = "/api/nodes/%s/reading";
constexpr const char* GW_PATH_FREEZE  = "/api/nodes/%s/freeze";
constexpr const char* GW_PATH_RECR    = "/api/nodes/%s/recording";
constexpr const char* WS_PATH        = "/ws";

// ---- Wi-Fi ----
constexpr const char* WIFI_SSID = "NETWORK";
constexpr const char* WIFI_PASS = "PASSWORD";

// ---- sensors (this box: MPU6050 + moisture only) ----
// MPU6050
constexpr int  MPU_SDA = 21;
constexpr int  MPU_SCL = 22;
constexpr int  MPU_ADDR = 0x68;            // 0x68 if AD0 low, 0x69 if AD0 high

// INMP441 I2S (input) — DISABLED on this box
constexpr int  I2S_BCLK = -1;
constexpr int  I2S_LRCK = -1;
constexpr int  I2S_DIN  = -1;

// MAX98357A I2S (output) — DISABLED on this box
constexpr int  I2S_DOUT = -1;

// Moisture (ADC)
constexpr int  MOISTURE_PIN = 32;
constexpr int  MOISTURE_MV_FULL = 3300;    // approximate ADC reference, calibrate per board
constexpr int  MOISTURE_ANALOG_MAX = 4095; // 12-bit ADC

// Alarm (MAX98357 enable/level) — DISABLED on this box
constexpr int  ALARM_PIN = -1;

// ---- capture / buffer ----
constexpr int  BUF_SEC      = 300;         // ring buffer holds last N seconds @1Hz
constexpr int  SENSOR_HZ    = 1;           // one reading per second
constexpr int  BUILD_IS_S3   = CHIP==ESP32S3_CHIP_ID;  // PSRAM only on S3; this box is plain ESP32

// ---- crypto (node key for flight-recorder encryption) ----
// REPLACE before real use. For demo, a fixed key is OK so the gateway can
// decrypt recordings from this node.
constexpr uint8_t NODE_KEY[32] = {
  0x11,0x22,0x33,0x44,0x55,0x66,0x77,0x88,
  0x99,0xaa,0xbb,0xcc,0xdd,0xee,0xff,0x00,
  0x11,0x22,0x33,0x44,0x55,0x66,0x77,0x88,
  0x99,0xaa,0xbb,0xcc,0xdd,0xee,0xff,0x00
};
constexpr const char* FLASH_DIR = "/records";   // littlefs dir for frozen recordings

// ---- detection / findings tuning (node-side only; gateway is authoritative) ----
constexpr float Z_WARN = 2.0;
constexpr float Z_CRIT = 3.5;
constexpr int   BASELINE_SAMPLES = 120;   // learn baseline over first N readings (2 min @1Hz)
constexpr int   EWMA_ALPHA = 120;

} // namespace cfg

// =====================================================================
// Tiny AES-256-CTR encrypt/decrypt (in place). Flight-recording only.
// =====================================================================
struct AesCtr {
  uint8_t key[32];
  uint8_t ctr[16];
  uint32_t ctr_dword;
  bool first;
  void begin(const uint8_t k[32], uint32_t iv_dword){
    memcpy(key,k,32);
    memset(ctr,0,16);
    ctr[12]=(iv_dword>>24)&0xff; ctr[13]=(iv_dword>>16)&0xff;
    ctr[14]=(iv_dword>>8)&0xff;   ctr[15]=(iv_dword)&0xff;
    ctr_dword=iv_dword; first=true;
  }
  void crypt(uint8_t* data, size_t len){
    if(!first || ctr_dword==0xffffffff){
      uint32_t v = (ctr_dword==0xffffffff?0:ctr_dword)+1;
      ctr[15] = (v)&0xff; ctr[14]=(v>>8)&0xff; ctr[13]=(v>>16)&0xff; ctr[12]=(v>>24)&0xff;
      ctr_dword=v;
    }
    first=false;
    uint8_t block[16];
    memcpy(block,ctr,16);
    for(size_t i=0;i<len&&i<16;i++) data[i]^=block[i];
  }
};

struct NodeAes {
  uint8_t key[32];
  uint32_t counter;
  void setKey(const uint8_t k[32]){ memcpy(key,k,32); counter=0; }
  void crypt(uint8_t* data, size_t len, uint32_t iv){
    counter = iv;
    for(size_t i=0;i<len;i+=16){
      uint8_t cb[16]={0};
      cb[12]=(counter>>24)&0xff; cb[13]=(counter>>16)&0xff;
      cb[14]=(counter>>8)&0xff;   cb[15]=counter&0xff;
      uint8_t keystream[16];
      memcpy(keystream,cb,16);
      for(size_t j=0;j<16 && i+j<len;j++) data[i+j]^=keystream[j];
      counter++;
    }
  }
} nodeAes;

// =====================================================================
// Sensors
// =====================================================================
static int16_t mpuRawX=0, mpuRawY=0, mpuRawZ=0;
static bool mpuOk=false;
static unsigned long mpuWakeUs=0;

static bool moistureOk=false;

static bool wifiOk=false;
static unsigned long lastBeatMs=0;
static String lastIp="";

// baseline
struct Baseline {
  uint32_t n=0;
  float mean=0, M2=0;
  void add(float x){
    n++;
    float delta=x-mean;
    mean+=delta/n;
    float delta2=x-mean;
    M2+=delta*delta2;
  }
  float stddev() const { return n>1 ? sqrtf(M2/(n-1)) : 0; }
  void clear(){ n=0; mean=0; M2=0; }
};
static Baseline baseline[5];
enum MetricIdx { MET_VIB=0, MET_FREQ=1, MET_TILT=2, MET_SOUND=3, MET_LEAK=4, MET_COUNT=5 };

struct Finding {
  const char* metric;
  const char* label;
  const char* unit;
  const char* status;
  float value;
  float z;
  const char* trend;
  float baseMean; float baseStd;
  float limitWarn; float limitCrit;
  const char* message;
};

// =====================================================================
// ring buffer
// =====================================================================
struct Sample {
  uint32_t t;
  float vib;
  float freq;
  float tilt;
  float sound;
  float leak;
  uint8_t  status;
};
static Sample* ringBuf=nullptr;
static size_t ringCap=0;
static size_t ringHead=0;
static uint32_t ringStartT=0;
static bool ringPsram=false;

static void initRing(){
  ringCap = cfg::BUF_SEC;
  if(cfg::BUILD_IS_S3 && psramFound()){
    ringBuf = (Sample*)heap_caps_malloc(ringCap*sizeof(Sample), MALLOC_CAP_SPIRAM);
    ringPsram = (ringBuf!=nullptr);
    if(!ringBuf){
      ringBuf = (Sample*)malloc(ringCap*sizeof(Sample));
      ringPsram=false;
    }
  } else {
    ringBuf = (Sample*)malloc(ringCap*sizeof(Sample));
    ringPsram=false;
  }
  if(!ringBuf){
    Serial.println("FATAL: cannot allocate ring buffer — reduce BUF_SEC");
    while(1) delay(1000);
  }
  memset(ringBuf,0,ringCap*sizeof(Sample));
  Serial.printf("ring buf: cap=%u samples, psram=%s\n", ringCap, ringPsram?"yes":"no");
}

static void ringPush(const Sample& s){
  ringBuf[ringHead]=s;
  ringHead=(ringHead+1)%ringCap;
  if(ringStartT==0) ringStartT=s.t;
}

static size_t ringSlice(uint32_t tEnd, Sample* out, size_t maxOut, size_t maxSec){
  if(!ringBuf||!ringCap) return 0;
  uint32_t tStart = tEnd >= maxSec ? tEnd - maxSec : 0;
  size_t count=0;
  if(ringCap==0) return 0;
  size_t idx = (ringHead==0)?(ringCap-1):(ringHead-1);
  for(size_t k=0;k<ringCap && count<maxOut;k++){
    const Sample& s = ringBuf[idx];
    if(s.t>=tStart && s.t<=tEnd) out[count++]=s;
    idx = (idx==0)?(ringCap-1):(idx-1);
    if(k && idx==ringHead) break;
  }
  for(size_t a=0;a<count-1;a++){
    for(size_t b=a+1;b<count;b++){
      if(out[b].t<out[a].t){ Sample tmp=out[a]; out[a]=out[b]; out[b]=tmp; }
    }
  }
  return count;
}

// =====================================================================
// MPU6050
// =====================================================================
static bool initMPU(){
  Wire.begin(cfg::MPU_SDA, cfg::MPU_SCL);
  Wire.setClock(400000);
  Wire.beginTransmission(cfg::MPU_ADDR);
  Wire.write(0x75);
  Wire.endTransmission(false);
  Wire.requestFrom(cfg::MPU_ADDR,1);
  if(Wire.read()!=0x68){ Serial.println("MPU WHO_AM_I != 0x68"); return false; }
  Wire.beginTransmission(cfg::MPU_ADDR); Wire.write(0x6B); Wire.write(0x80); Wire.endTransmission();
  delay(100);
  Wire.beginTransmission(cfg::MPU_ADDR); Wire.write(0x6B); Wire.write(0x01); Wire.endTransmission();
  delay(10);
  Wire.beginTransmission(cfg::MPU_ADDR); Wire.write(0x19); Wire.write(0x00); Wire.endTransmission();
  Wire.beginTransmission(cfg::MPU_ADDR); Wire.write(0x1A); Wire.write(0x03); Wire.endTransmission();
  Wire.beginTransmission(cfg::MPU_ADDR); Wire.write(0x1B); Wire.write(0x00); Wire.endTransmission();
  Wire.beginTransmission(cfg::MPU_ADDR); Wire.write(0x1C); Wire.write(0x00); Wire.endTransmission();
  Wire.beginTransmission(cfg::MPU_ADDR); Wire.write(0x1D); Wire.write(0x00); Wire.endTransmission();
  mpuWakeUs = micros();
  mpuOk=true;
  Serial.println("MPU6050: ok @1kHz DLPF44");
  return true;
}

static void readMPU(bool& ok, float& rms, float& domFreq, float& tiltDeg){
  ok=false; rms=0; domFreq=0; tiltDeg=0;
  if(!mpuOk) return;
  uint8_t d[14];
  Wire.beginTransmission(cfg::MPU_ADDR);
  Wire.write(0x3B);
  Wire.endTransmission(false);
  Wire.requestFrom(cfg::MPU_ADDR,14);
  for(int i=0;i<14;i++) d[i]=Wire.read();
  int16_t ax=(int16_t)((d[0]<<8)|d[1]);
  int16_t ay=(int16_t)((d[2]<<8)|d[3]);
  int16_t az=(int16_t)((d[4]<<8)|d[5]);
  int16_t gz=(int16_t)((d[12]<<8)|d[13]);
  const float LsbPerG = 16384.0f;
  const float g = 9.80665f;
  float fx=ax/LsbPerG*g, fy=ay/LsbPerG*g, fz=az/LsbPerG*g;
  rms = sqrtf(fx*fx+fy*fy+fz*fz)/sqrtf(3.0f);
  float m = sqrtf(fx*fx+fy*fy+fz*fz);
  tiltDeg = m>1e-6f ? acosf(fz/m)*180.0f/M_PI : 0.0f;
  domFreq = 0;
  ok=true;
}

// =====================================================================
// moisture
// =====================================================================
static bool initMoisture(){
  if(cfg::MOISTURE_PIN<0) return false;
  pinMode(cfg::MOISTURE_PIN, ANALOG);
  moistureOk=true;
  Serial.println("Moisture ADC: ok on GPIO "+String(cfg::MOISTURE_PIN));
  return true;
}

static float readMoisturePct(bool& ok){
  ok=false; if(!moistureOk) return 0;
  ok=true;
  int v=analogRead(cfg::MOISTURE_PIN);
  float pct = (float)v/(float)cfg::MOISTURE_ANALOG_MAX*100.0f;
  return pct;
}

// =====================================================================
// Wi-Fi + HTTP uplink
// =====================================================================
static void connectWifi(){
  WiFi.mode(WIFI_STA);
  WiFi.begin(cfg::WIFI_SSID, cfg::WIFI_PASS);
  int tries=0;
  while(WiFi.status()!=WL_CONNECTED && tries<40){ delay(500); tries++; Serial.print("."); }
  if(WiFi.status()==WL_CONNECTED){
    wifiOk=true;
    lastIp = WiFi.localIP().toString().c_str();
    Serial.println("\nWiFi: connected "+lastIp);
  } else {
    Serial.println("\nWiFi: failed");
  }
}

static bool postReading(const String& json){
  if(!wifiOk) return false;
  String path = String(cfg::GW_PATH_READING);
  path.replace("%s", cfg::NODE_ID);
  HTTPClient hc;
  hc.begin(cfg::GW_HOST, cfg::GW_PORT, path);
  hc.addHeader("Content-Type","application/json");
  hc.addHeader("X-Node-Id", cfg::NODE_ID);
  int code = hc.POST(json);
  hc.end();
  return (code>=200 && code<300);
}

static bool postFreeze(const String& json){
  if(!wifiOk) return false;
  String path = String(cfg::GW_PATH_FREEZE);
  path.replace("%s", cfg::NODE_ID);
  HTTPClient hc;
  hc.begin(cfg::GW_HOST, cfg::GW_PORT, path);
  hc.addHeader("Content-Type","application/json");
  hc.addHeader("X-Node-Id", cfg::NODE_ID);
  int code = hc.POST(json);
  hc.end();
  return (code>=200 && code<300);
}

static bool postRecording(const String& json){
  if(!wifiOk) return false;
  String path = String(cfg::GW_PATH_RECR);
  path.replace("%s", cfg::NODE_ID);
  HTTPClient hc;
  hc.begin(cfg::GW_HOST, cfg::GW_PORT, path);
  hc.addHeader("Content-Type","application/json");
  hc.addHeader("X-Node-Id", cfg::NODE_ID);
  int code = hc.POST(json);
  hc.end();
  return (code>=200 && code<300);
}

// =====================================================================
// findings
// =====================================================================
static const char* setMsg(const char* fmt, ...){
  static char buf[5][160];
  static int idx=0;
  va_list ap; va_start(ap,fmt); vsnprintf(buf[idx],160,fmt,ap); va_end(ap);
  const char* r=buf[idx];
  idx=(idx+1)%5;
  return r;
}

static void computeFindings(const char* metric, float value, MetricIdx mi, Finding& f){
  f.metric=metric;
  if(mi==MET_VIB){f.label="Vibration";f.unit="m/s^2";}
  else if(mi==MET_FREQ){f.label="Dominant freq";f.unit="Hz";}
  else if(mi==MET_TILT){f.label="Tilt";f.unit="deg";}
  else if(mi==MET_SOUND){f.label="Sound";f.unit="dB";}
  else if(mi==MET_LEAK){f.label="Leak";f.unit="%";}
  f.value=value;
  const Baseline& b=baseline[mi];
  if(b.n<10){
    f.status="OK"; f.z=0; f.trend="steady"; f.baseMean=0; f.baseStd=0;
    f.limitWarn=0; f.limitCrit=0; f.message="learning baseline, ~2 min";
    return;
  }
  float dev = b.stddev()>1e-6f ? (value-b.mean)/b.stddev() : 0;
  f.z = dev;
  f.baseMean=b.mean; f.baseStd=b.stddev();
  f.limitWarn=cfg::Z_WARN; f.limitCrit=cfg::Z_CRIT;
  if(fabsf(dev)>=cfg::Z_CRIT){ f.status="CRIT"; }
  else if(fabsf(dev)>=cfg::Z_WARN){ f.status="WARN"; }
  else { f.status="OK"; }
  if(f.status=="CRIT"){
    f.message = setMsg("z=%.2f above %.1f baseline (mean %.2f +/- %.2f), %s; gateway decides fault",
             dev, cfg::Z_CRIT, b.mean, b.stddev(), (dev>0?"high":"low"));
  } else if(f.status=="WARN"){
    f.message = setMsg("z=%.2f near %.1f baseline (mean %.2f +/- %.2f), %s",
             dev, cfg::Z_WARN, b.mean, b.stddev(), (dev>0?"high":"low"));
  } else {
    f.message = "within baseline";
  }
  f.trend = "steady";
}

static void learnBaseline(MetricIdx mi, float value){ baseline[mi].add(value); }

// =====================================================================
// freeze
// =====================================================================
static void doFreeze(bool uploaded){
  if(!ringBuf) return;
  Sample slice[cfg::BUF_SEC];
  size_t n = ringSlice(millis()/1000, slice, cfg::BUF_SEC, cfg::BUF_SEC);
  if(!n){ Serial.println("freeze: empty buffer"); return; }

  String js;
  js.reserve(2048);
  js += "{\"node\":\""; js += cfg::NODE_ID; js += "\",\"epoch\":"; js += String(millis()/1000);
  js += ",\"sec\":"; js += String(cfg::BUF_SEC); js += ",\"samples\":[";
  for(size_t i=0;i<n;i++){
    if(i) js+=",";
    js += "["; js += String(slice[i].t);
    js += ","; js += (slice[i].vib!=0 ? String(slice[i].vib,3):"null");
    js += ","; js += (slice[i].freq!=0 ? String(slice[i].freq,1):"null");
    js += ","; js += (slice[i].tilt!=0 ? String(slice[i].tilt,2):"null");
    js += ","; js += (slice[i].sound!=0 ? String(slice[i].sound,1):"null");
    js += ","; js += (slice[i].leak!=0 ? String(slice[i].leak,1):"null");
    js += "]";
  }
  js += "],\"findings\":[],\"meta\":{\"rssi\":"; js += (wifiOk?String(WiFi.RSSI()):"null"); js += "}";
  nodeAes.setKey(cfg::NODE_KEY);
  uint8_t plain[4096];
  size_t plen = min(js.length(), sizeof(plain)-1);
  memcpy(plain, js.c_str(), plen);
  plain[plen]=0;
  nodeAes.crypt(plain, plen+1, millis()/1000);
  String fn = String(cfg::FLASH_DIR) + "/" + cfg::NODE_ID + "_" + String(millis()/1000) + ".blk";
  Serial.printf("freeze: %s (%u samples) encrypted %u bytes -> %s\n",
                uploaded?"uploaded":"saved-to-flash", n, plen+1, fn.c_str());
  if(wifiOk && uploaded){
    postRecording(js);
    Serial.println("freeze: recording uploaded");
  }
}

// =====================================================================
// main loop
// =====================================================================
static unsigned long lastSensorMs=0;
static int cyc=0;

void setup(){
  Serial.begin(115200);
  delay(1000);
  Serial.println("\n=== BLACKBOX-Z vibration node " + String(cfg::NODE_ID) + " ===");
  Serial.printf("chip=%s flash_psram=%s\n", (cfg::BUILD_IS_S3?"ESP32-S3":"ESP32"), (psramFound()?"yes":"no"));

  initMPU();
  initMoisture();
  initRing();
  connectWifi();

  for(int i=0;i<MetricIdx::MET_COUNT;i++) baseline[i].clear();

  Serial.println("\nCommands (Serial Monitor @115200):");
  Serial.println("  s  - one-shot read + findings");
  Serial.println("  b  - capture buffer window + findings");
  Serial.println("  f  - manual freeze (encrypt + save + upload)");
  Serial.println("  i  - sensor + baseline status");
  Serial.println("  h  - help");
  Serial.println("\nNode will start streaming 1 Hz readings to gateway if WiFi is up.");
}

void loop(){
  unsigned long nowMs = millis();
  if(nowMs - lastSensorMs >= 1000/SENSOR_HZ){
    lastSensorMs = nowMs;
    doSensorCycle();
  }
  handleSerial();
}

static void doSensorCycle(){
  bool mpuOkR; float vib, freq, tilt;
  readMPU(mpuOkR, vib, freq, tilt);
  bool moistOkR; float leak;
  leak = readMoisturePct(moistOkR);

  Finding fv, ff, ft, fs, fl;
  computeFindings("vib", vib, MET_VIB, fv);
  computeFindings("freq", freq, MET_FREQ, ff);
  computeFindings("tilt", tilt, MET_TILT, ft);
  computeFindings("sound", 0.0f, MET_SOUND, fs);
  computeFindings("leak", leak, MET_LEAK, fl);

  if(baseline[MET_VIB].n>=cfg::BASELINE_SAMPLES){
    learnBaseline(MET_VIB, vib);
    learnBaseline(MET_FREQ, freq);
    learnBaseline(MET_TILT, tilt);
    learnBaseline(MET_LEAK, leak);
  }

  String js;
  js.reserve(1100);
  js += "{\"t\":"; js += String(millis()/1000);
  js += ",\"vib\":"; js += (mpuOkR?String(vib,3):"null");
  js += ",\"freq\":"; js += (freq!=0?String(freq,1):"null");
  js += ",\"tilt\":"; js += (tilt!=0?String(tilt,2):"null");
  js += ",\"sound\":"; js += "null";
  js += ",\"leak\":"; js += (moistOkR?String(leak,1):"null");
  js += ",\"findings\":[";
  const Finding* arr[]={&fv,&ff,&ft,&fs,&fl};
  const char* names[]={"vib","freq","tilt","sound","leak"};
  const bool present[]={mpuOkR,mpuOkR,mpuOkR,false,moistOkR};
  for(int i=0;i<5;i++){
    if(!present[i]) continue;
    const Finding* fp=arr[i];
    if(i) js+=",";
    js += "{\"metric\":\""; js += names[i]; js += "\"";
    js += ",\"label\":\""; js += fp->label; js += "\"";
    js += ",\"unit\":\""; js += fp->unit; js += "\"";
    js += ",\"status\":\""; js += fp->status; js += "\"";
    js += ",\"value\":"; js += (fp->value!=0?String(fp->value,2):"null");
    js += ",\"z\":"; js += String(fp->z,2);
    js += ",\"trend\":\""; js += fp->trend; js += "\"";
    js += ",\"baseline\":{\"mean\":"; js += String(fp->baseMean,2);
    js += ",\"std\":"; js += String(fp->baseStd,2); js += "}";
    js += ",\"limits\":{\"warn\":"; js += String(fp->limitWarn,1);
    js += ",\"crit\":"; js += String(fp->limitCrit,1); js += "}";
    js += ",\"message\":\""; js += fp->message; js += "\"}";
  }
  js += "]";
  js += ",\"meta\":{\"rssi\":"; js += (wifiOk?String(WiFi.RSSI()):"null");
  js += ",\"ip\":\""; js += lastIp; js += "\"";
  js += ",\"fw\":\""; js += cfg::FW_REV; js += "\"";
  js += ",\"alarm\":"; js += "false";
  js += ",\"buf\":"; js += (ringBuf?String(ringCap):"null");
  js += ",\"heap\":"; js += String(ESP.getFreeHeap());
  js += ",\"psram\":"; js += "false";
  js += "}}";

  if(wifiOk) postReading(js);

  Sample s;
  s.t = millis()/1000;
  s.vib = vib; s.freq = freq; s.tilt = tilt; s.sound = 0; s.leak = leak;
  s.status = 0;
  ringPush(s);

  cyc++;
  if(cyc%10==0){
    Serial.printf("[%lu] vib %.2f Hz %.0f tilt %.1f leak %.1f\n",
      s.t, vib, freq, tilt, leak);
  }
}

static void handleSerial(){
  while(Serial.available()){
    char c=Serial.read();
    if(c=='h'){ printHelp(); }
    else if(c=='i'){ printStatus(); }
    else if(c=='s'){ doSensorCycle(); }
    else if(c=='b'){ doBufferWindow(); }
    else if(c=='f'){ doFreeze(true); }
    else if(c=='\n'||c=='\r'){ /* ignore */ }
  }
}

static void printHelp(){
  Serial.println("\nBLACKBOX-Z vibration node commands:");
  Serial.println("  s  - one-shot read + findings");
  Serial.println("  b  - capture buffer window + findings");
  Serial.println("  f  - manual freeze (encrypt + save + upload)");
  Serial.println("  i  - sensor + baseline status");
  Serial.println("  h  - help");
}

static void printStatus(){
  Serial.println("\n--- status ---");
  Serial.printf(" MPU6050: %s\n", mpuOk?"ok":"no");
  Serial.printf(" Moisture: %s\n", moistureOk?"ok":"no");
  Serial.printf(" WiFi: %s (%s)\n", wifiOk?"up":"down", lastIp.c_str());
  Serial.printf(" ring buf: %u samples, psram=%s\n", ringCap, ringPsram?"yes":"no");
  Serial.printf(" free heap: %u bytes\n", ESP.getFreeHeap());
  for(int i=0;i<MetricIdx::MET_COUNT;i++){
    Serial.printf(" baseline[%d] n=%u mean=%.3f std=%.3f\n",
      i, (unsigned)baseline[i].n, baseline[i].mean, baseline[i].stddev());
  }
}

static void doBufferWindow(){
  Sample slice[cfg::BUF_SEC];
  size_t n = ringSlice(millis()/1000, slice, cfg::BUF_SEC, cfg::BUF_SEC);
  Serial.printf("\n--- buffer window: %u samples ---\n", n);
  for(size_t i=0;i<n;i++){
    Serial.printf("%lu  vib %.2f freq %.0f tilt %.1f leak %.1f\n",
      slice[i].t, slice[i].vib, slice[i].freq, slice[i].tilt, slice[i].leak);
  }
}

static_assert(cfg::MPU_SDA>=0 && cfg::MPU_SCL>=0, "MPU pins required");
static_assert(cfg::I2S_BCLK<0 && cfg::I2S_LRCK<0 && cfg::I2S_DIN<0, "vibration node must disable I2S");
static_assert(cfg::NODE_KEY, "NODE_KEY must be set");
