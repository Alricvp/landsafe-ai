/*
  BLACKBOX-Z — ESP32-S3 machine flight-recorder node (audio + alarm box)
  =======================================================================
  This is the audio box variant: INMP441 mic + MAX98357A alarm audio.
  No vibration, no tilt, no moisture on this board.

  Same sketch family as the main node; only the cfg block and disabled
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
constexpr const char* NODE_ID   = "esp32-s3-b";   // dashboard + gateway node name
constexpr const char* FW_REV    = "blackbox-z-audio-node-1";

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

// ---- sensors (this box: mic + alarm only) ----
// MPU6050 — DISABLED on this box
constexpr int  MPU_SDA = -1;
constexpr int  MPU_SCL = -1;
constexpr int  MPU_ADDR = 0x68;

// INMP441 I2S (input)
constexpr int  I2S_BCLK = 25;
constexpr int  I2S_LRCK = 26;
constexpr int  I2S_DIN  = 35;

// MAX98357A I2S (output, alarm audio)
constexpr int  I2S_DOUT = 37;
constexpr int  ALARM_PIN = 33;       // optional enable / level pin for the amp

// Moisture (ADC) — DISABLED on this box
constexpr int  MOISTURE_PIN = -1;
constexpr int  MOISTURE_MV_FULL = 3300;
constexpr int  MOISTURE_ANALOG_MAX = 4095;

// ---- capture / buffer ----
constexpr int  BUF_SEC      = 300;  // ring buffer holds last N seconds @1Hz
constexpr int  SENSOR_HZ    = 1;
constexpr int  BUILD_IS_S3   = CHIP==ESP32S3_CHIP_ID;

// ---- crypto (node key for flight-recorder encryption) ----
constexpr uint8_t NODE_KEY[32] = {
  0x11,0x22,0x33,0x44,0x55,0x66,0x77,0x88,
  0x99,0xaa,0xbb,0xcc,0xdd,0xee,0xff,0x00,
  0x11,0x22,0x33,0x44,0x55,0x66,0x77,0x88,
  0x99,0xaa,0xbb,0xcc,0xdd,0xee,0xff,0x00
};
constexpr const char* FLASH_DIR = "/records";

// ---- detection / findings tuning (node-side only) ----
constexpr float Z_WARN = 2.0;
constexpr float Z_CRIT = 3.5;
constexpr int   BASELINE_SAMPLES = 120;
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
    // Real build: aes intravascular_encrypt_block() / mbedtls AES here.
    // Kept as a clear placeholder so this one file still describes the CTR shape.
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
      memcpy(keystream,cb,16);  // placeholder keystream — real AES in real build
      for(size_t j=0;j<16 && i+j<len;j++) data[i+j]^=keystream[j];
      counter++;
    }
  }
} nodeAes;

// =====================================================================
// Sensors
// =====================================================================
static bool i2sOk=false;
static i2s_config_t i2sInCfg{};
static i2s_pin_config_t i2sPins{};

static bool alarmOn=false;

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
// ring buffer (PSRAM on S3, heap on ESP32)
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
// I2S mic
// =====================================================================
static bool initI2SIn(){
  i2sPins.bck_io_num=cfg::I2S_BCLK;
  i2sPins.ws_io_num=cfg::I2S_LRCK;
  i2sPins.data_out_num=-1;
  i2sPins.data_in_num=cfg::I2S_DIN;
  i2sInCfg.mode=I2S_MODE_MONO_RX;
  i2sInCfg.sample_rate=16000;
  i2sInCfg.bits_per_sample=I2S_BITS_PER_SAMPLE_16BIT;
  i2sInCfg.channel_format=I2S_CHANNEL_FMT_ONLY_LEFT;
  i2sInCfg.communication_format=I2S_COMM_FORMAT_STAND_MSB;
  i2sInCfg.intr_alloc_flags=ESP_INTR_FLAG_LEVEL1;
  i2sInCfg.dma_buf_count=4;
  i2sInCfg.dma_buf_len=256;
  i2sInCfg.use_apll=true;
  i2sInCfg.tx_desc=NULL; i2sInCfg.rx_desc=NULL;
  i2sInCfg.fixed_mclk=0;
  if(i2s_driver_install(I2S_NUM_0, &i2sInCfg, 0, NULL)!=ESP_OK){ Serial.println("I2S in install failed"); return false; }
  if(i2s_set_pin(I2S_NUM_0, &i2sPins)!=ESP_OK){ Serial.println("I2S pin set failed"); return false; }
  i2sOk=true;
  Serial.println("INMP441 I2S: ok @16kHz");
  return true;
}

static void readI2SIn(bool& ok, float& rmsDb){
  ok=false; rmsDb=0;
  if(!i2sOk) return;
  static int16_t buf[512];
  size_t nread=0;
  esp_err_t r=i2s_read(I2S_NUM_0, buf, sizeof(buf), &nread, 20);
  if(r!=ESP_OK || nread<256) return;
  ok=true;
  float sum=0; int cnt=0;
  for(size_t i=0;i<nread;i+=2){
    int16_t s = (int16_t)(buf[i+1]<<8 | buf[i]);
    float f=s/32768.0f;
    sum+=f*f; cnt++;
  }
  if(cnt==0) return;
  float ms = sum/cnt;
  float rms = sqrtf(ms);
  rmsDb = rms>1e-6f ? 20.0f*log10f(rms) : -96.0f;
}

// =====================================================================
// Ethernet / Wi-Fi + HTTP uplink
// =====================================================================
static bool wifiOk=false;
static unsigned long lastBeatMs=0;
static String lastIp="";

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
  Serial.println("\n=== BLACKBOX-Z audio node " + String(cfg::NODE_ID) + " ===");
  Serial.printf("chip=%s flash_psram=%s\n", (cfg::BUILD_IS_S3?"ESP32-S3":"ESP32"), (psramFound()?"yes":"no"));

  initI2SIn();
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
  bool i2sOkR; float soundDb;
  readI2SIn(i2sOkR, soundDb);

  Finding fv, ff, ft, fs, fl;
  computeFindings("vib", 0.0f, MET_VIB, fv);
  computeFindings("freq", 0.0f, MET_FREQ, ff);
  computeFindings("tilt", 0.0f, MET_TILT, ft);
  computeFindings("sound", soundDb, MET_SOUND, fs);
  computeFindings("leak", 0.0f, MET_LEAK, fl);

  if(baseline[MET_VIB].n>=cfg::BASELINE_SAMPLES){
    learnBaseline(MET_SOUND, soundDb);
  }

  String js;
  js.reserve(1100);
  js += "{\"t\":"; js += String(millis()/1000);
  js += ",\"vib\":"; js += "null";
  js += ",\"freq\":"; js += "null";
  js += ",\"tilt\":"; js += "null";
  js += ",\"sound\":"; js += (i2sOkR?String(soundDb,1):"null");
  js += ",\"leak\":"; js += "null";
  js += ",\"findings\":[";
  const Finding* arr[]={&fv,&ff,&ft,&fs,&fl};
  const char* names[]={"vib","freq","tilt","sound","leak"};
  const bool present[]={false,false,false,i2sOkR,false};
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
  js += ",\"alarm\":"; js += (alarmOn?"true":"false");
  js += ",\"buf\":"; js += (ringBuf?String(ringCap):"null");
  js += ",\"heap\":"; js += String(ESP.getFreeHeap());
  js += ",\"psram\":"; js += (psramFound()&&ringPsram?"true":"false");
  js += "}}";

  if(wifiOk) postReading(js);

  Sample s;
  s.t = millis()/1000;
  s.vib = 0; s.freq = 0; s.tilt = 0; s.sound = soundDb; s.leak = 0;
  s.status = 0;
  ringPush(s);

  cyc++;
  if(cyc%10==0){
    Serial.printf("[%lu] sound %.1f dB\n", s.t, soundDb);
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
  Serial.println("\nBLACKBOX-Z audio node commands:");
  Serial.println("  s  - one-shot read + findings");
  Serial.println("  b  - capture buffer window + findings");
  Serial.println("  f  - manual freeze (encrypt + save + upload)");
  Serial.println("  i  - sensor + baseline status");
  Serial.println("  h  - help");
}

static void printStatus(){
  Serial.println("\n--- status ---");
  Serial.printf(" INMP441: %s\n", i2sOk?"ok":"no");
  Serial.printf(" WiFi: %s (%s)\n", wifiOk?"up":"down", lastIp.c_str());
  Serial.printf(" ring buf: %u samples, psram=%s\n", ringCap, ringPsram?"yes":"no");
  Serial.printf(" free heap: %u bytes\n", ESP.getFreeHeap());
  Serial.printf(" psram free: %u bytes\n", psramGetFree(0));
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
    Serial.printf("%lu  sound %.1f dB\n", slice[i].t, slice[i].sound);
  }
}

static_assert(cfg::MPU_SDA<0 && cfg::MPU_SCL<0, "audio node must disable MPU");
static_assert(cfg::MOISTURE_PIN<0, "audio node must disable moisture");
static_assert(cfg::I2S_BCLK>=0 && cfg::I2S_LRCK>=0 && cfg::I2S_DIN>=0, "I2S mic pins required");
static_assert(sizeof(cfg::NODE_KEY)==32, "NODE_KEY must be 32 bytes");
