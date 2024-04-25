
#include <ESP8266WiFi.h>
#include <WiFiClientSecure.h>
#include <PubSubClient.h>
#include <NTPClient.h>
// Global Variables
int Bias = 512;                           // Nominally half of the 1023 range   Adjust as necessary              
int Analog;                               // The analog reading with bias subtracted-out and converted to absolute value (Read from A0)  
int Max;                                  // The maximum peak 
int LoopTime = 50;                      // Read continuously in a fast-loop for one second before finding peak & calculating average
int SPLref = 94;                          // An arbritary (semi-standard) reference for finding PeakRef and AvgRef. Any known SPL level will work
int PeakRef = 159;                        // Measured (or calculated) at SPLref
int AvgRef = 73;                          // Measured (or calculated) at SPLref
int n;                                    // Number of readings in the loop (for calculatijng the average)
int PeakThreshold = 124;
int ThreshTime = 15000;
int GracePeriod = 1 * 1000;                // (left number is #seconds) Number of milliseconds of grace given between potential peak readings
int NumPeaksPermitted = 0;
int NumPeaks;


unsigned long Sum;                        // For finding average
unsigned long ReadStartTime;              // millis() used for SampleTime loop
unsigned long ThreshStartTime;            // millis() used for TreshTime loop
unsigned long GraceTime;                 // millis() used in between peaks to make sure one loud sound doesn't count multiple times

float Average;                           // ADC average
float dBSPLPeak;                         // Peak dB SPL reading.   
float dBSPLAvg;                          // Average SPL reading

String message = "YOUR ASS AT APEX";
String AlertID = "12345";
/****** WiFi Connection Details *******/
const char* ssid = "Stevens-IoT";
const char* password = "ATu466wsH4";

/******* MQTT HiveMQ Cloud Connection Details *******/
const char* mqtt_server = "7a9481a885f646fda619cbcfe91f0802.s1.eu.hivemq.cloud";
const char* mqtt_username = "KovacsDargos";
const char* mqtt_password = "ibPXbf0FKe";
const int mqtt_port = 8883;



/**** Secure WiFi Connectivity Initialisation *****/
WiFiClientSecure espClient;

/**** MQTT Client Initialisation Using WiFi Connection *****/
PubSubClient client(espClient);


void setup_wifi() {
  delay(10);
  Serial.print("\nConnecting to ");
  Serial.println(ssid);

  WiFi.mode(WIFI_STA);
  WiFi.begin(ssid, password);

  while (WiFi.status() != WL_CONNECTED) {
    delay(500);
    Serial.print(".");
  }
  randomSeed(micros());
  Serial.println("\nWiFi connected\nIP address: ");
  Serial.println(WiFi.localIP());
}

void reconnect() {
  // Loop until we're reconnected
  while (!client.connected()) {
    Serial.print("Attempting MQTT connection...");
    String clientId = "ESP8266Client-";   // Create a random client ID
    clientId += String(random(0xffff), HEX);
    // Attempt to connect
    if (client.connect(clientId.c_str(), mqtt_username, mqtt_password)) {
      Serial.println("connected");
    } else {
      Serial.print("failed, rc=");
      Serial.print(client.state());
      Serial.println(" try again in 5 seconds");   // Wait 5 seconds before retrying
      delay(5000);
    }
  }
}
void publishMessage(const char* topic, String payload , boolean retained){
  if (client.publish(topic, payload.c_str(), true))
      Serial.println("Message publised ["+String(topic)+"]: "+payload);
}

void handleDisconnect(){
 Serial.print("Disconnected from MQTT broker. Error code: ");
  Serial.println(client.state());
}
//==============================================================================================================  
void setup()
{   
  Serial.begin(9600);                   // Used for serial monitor
  NumPeaks = 0;
  setup_wifi(); 
  espClient.setInsecure();
  client.setServer(mqtt_server, mqtt_port);
  client.setKeepAlive(4);
 
}

// Start main loop ============================================================================================
void loop()
{
  if (!client.connected()) {
    handleDisconnect();
    reconnect();
    } // check if client is connected
  client.loop();
  
  Max = 0;                                  //Initilize/reset every time before starting while() loop
  Sum = 0;
  n = 0;                                    //Number of readings (number of loops counted in 1 second)

  if(millis() - ThreshStartTime > ThreshTime){ // If ThreshTime has been reached, then everything resets as you have been quiet for long enough
    Serial.println("ThreshStartTime reset!");
    ThreshStartTime = millis();
    NumPeaks = 0;
  }
 
  ReadStartTime = millis();                 //Save/update loop-starting time

  // Find maximum & accumulate sum loop ==================================================================================
  // Takes readings in a "fast loop" to find the peak & average.  
  while (millis() - ReadStartTime < LoopTime)            
  {
    Analog = abs(analogRead(A0) - Bias);                 // Read, take out the 3.3V bias/offset, make positive. 
    if (Analog > Max)                                    
      Max = Analog;                                      // Save overall maximum reading (Zero is invalid for log/dB calculation)
  
    Sum = Sum + Analog;
    n++;                                                 // Count the number of readings (to calculate average)
  }  // of while() loop ===================================================================================================

  Average = (float)Sum/n;                                // Zero is invalid for log/dB calculation 

  if(Average > PeakThreshold && (millis() - GraceTime > GracePeriod)){ // If you break the threshold, peak counter is increased
    NumPeaks = NumPeaks + 1;
    GraceTime = millis();
    Serial.print(NumPeaks);
    Serial.println(": Peak Added");
    ThreshStartTime = millis();
    

  }
  if(NumPeaks > NumPeaksPermitted){
    Serial.println("TOO LOUD CALM DOWN");       //Send Alert
    String alert = "Alerts";
    alert.concat(AlertID);
    publishMessage(alert.c_str(), message.c_str(), true);
    NumPeaks = 0;
    ThreshStartTime = millis();
  }

  
}  // End of main loop ==========================================================================================