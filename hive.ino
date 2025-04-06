#include <ESP8266WiFi.h>
#include <WiFiClientSecure.h>
#include <PubSubClient.h>

// WiFi credentials
const char* ssid = "YOUR_WIFI_SSID";
const char* password = "YOUR_WIFI_PASSWORD";

// HiveMQ Cloud MQTT Broker settings
const char* mqtt_server = "YOUR_HIVEMQ_URL"; // Your HiveMQ broker address
const int mqtt_port = 8883; // Port 8883 for MQTT over TLS
const char* mqtt_username = "YOUR_HIVEMQ_USERNAME"; // Replace with credentials you create in HiveMQ
const char* mqtt_password = "YOUR_HIVEMQ_PASSWORD"; // Replace with credentials you create in HiveMQ

// MQTT topic to subscribe to
const char* mqtt_topic = "nodemcu/control";

// Pin definitions
const int RELAY_PIN = D1;  // Pin connected to IN1 on the relay module

// Initialize the WiFi and MQTT clients
WiFiClientSecure espClient;  // Use secure client for TLS connection
PubSubClient client(espClient);

void setup_wifi() {
  delay(10);
  Serial.println();
  Serial.print("Connecting to ");
  Serial.println(ssid);

  WiFi.mode(WIFI_STA);
  WiFi.begin(ssid, password);

  while (WiFi.status() != WL_CONNECTED) {
    delay(500);
    Serial.print(".");
  }

  Serial.println("");
  Serial.println("WiFi connected");
  Serial.println("IP address: ");
  Serial.println(WiFi.localIP());
}

void callback(char* topic, byte* payload, unsigned int length) {
  // Convert payload to string
  String message;
  for (int i = 0; i < length; i++) {
    message += (char)payload[i];
  }
 
  Serial.print("Message arrived [");
  Serial.print(topic);
  Serial.print("] ");
  Serial.println(message);

  // Check if the message is "ON" or "OFF"
  if (message == "OFF") {
    digitalWrite(RELAY_PIN, HIGH); // Turn relay ON
    Serial.println("Relay turned ON");
  } else if (message == "ON") {
    digitalWrite(RELAY_PIN, LOW);  // Turn relay OFF
    Serial.println("Relay turned OFF");
  }
}

void reconnect() {
  // Loop until we're reconnected
  while (!client.connected()) {
    Serial.print("Attempting MQTT connection...");
   
    // Create a random client ID
    String clientId = "NodeMCU-";
    clientId += String(random(0xffff), HEX);
   
    // Attempt to connect
    if (client.connect(clientId.c_str(), mqtt_username, mqtt_password)) {
      Serial.println("connected");
     
      // Subscribe to our topic
      client.subscribe(mqtt_topic);
    } else {
      Serial.print("failed, rc=");
      Serial.print(client.state());
      Serial.println(" try again in 5 seconds");
      delay(5000);
    }
  }
}

void setup() {
  // Initialize pins
  pinMode(RELAY_PIN, OUTPUT);
 
  // Set initial states - both OFF
  digitalWrite(RELAY_PIN, LOW);  // Relay off
 
  // Start serial connection
  Serial.begin(9600);  // Changed to 9600 to match your example
  Serial.println("NodeMCU starting...");
  Serial.println("Relay is OFF initially");
 
  // Connect to WiFi
  setup_wifi();
 
  // Skip certificate validation - for development only
  // In production, use proper certificate validation
  espClient.setInsecure();
 
  // Set up MQTT client
  client.setServer(mqtt_server, mqtt_port);
  client.setCallback(callback);
}

void loop() {
  // Maintain MQTT connection
  if (!client.connected()) {
    reconnect();
  }
  client.loop();
}