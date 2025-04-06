# mqtt_mcp_server.py
import paho.mqtt.client as mqtt
import ssl
import time
from mcp.server import Server
from mcp import types
from fastapi import FastAPI, HTTPException
import uvicorn
from sse_starlette.sse import EventSourceResponse
import asyncio
from pydantic import BaseModel

# Initialize MCP Server logic
mcp_server = Server("MQTTControlServer")

# Create FastAPI app
app = FastAPI(title="MQTT Control MCP Server")

class MQTTControlTool:
    def __init__(self):
        # HiveMQ Connection Details
        self.broker_address = "YOUR_HIVEMQ_URL"
        self.broker_port = 8883  # TLS port
        self.username = "YOUR_HIVEMQ_USERNAME"  # Replace with your HiveMQ username
        self.password = "YOUR_HIVEMQ_PASSWORD"  # Replace with your HiveMQ password
        self.topic = "nodemcu/control"

    def _send_mqtt_command(self, command):
        """Internal method to send MQTT commands to the broker"""
        # Create a new client instance
        client = mqtt.Client()
        
        # Set TLS/SSL
        client.tls_set(cert_reqs=ssl.CERT_REQUIRED, tls_version=ssl.PROTOCOL_TLS)
        
        # Set authentication
        client.username_pw_set(self.username, self.password)
        
        # Connect callback
        def on_connect(client, userdata, flags, rc):
            if rc != 0:
                print(f"Failed to connect to MQTT broker. Error code: {rc}")
        
        # Publish callback
        def on_publish(client, userdata, mid):
            print(f"Message ID {mid} published successfully")
        
        # Set callbacks
        client.on_connect = on_connect
        client.on_publish = on_publish
        
        try:
            # Connect to broker
            client.connect(self.broker_address, self.broker_port, 60)
            
            # Start the loop
            client.loop_start()
            
            # Wait for connection to establish
            time.sleep(1)
            
            # Publish the message
            result = client.publish(self.topic, command, qos=1)
            result.wait_for_publish(timeout=5)
            
            # Wait a moment
            time.sleep(1)
            
            # Disconnect
            client.loop_stop()
            client.disconnect()
            return f"Successfully sent {command} command to device"
            
        except Exception as e:
            return f"Error sending command: {str(e)}"

    def turn_on(self):
        """Turn the relay ON"""
        return self._send_mqtt_command("ON")

    def turn_off(self):
        """Turn the relay OFF"""
        return self._send_mqtt_command("OFF")
    
    def send_custom_command(self, command):
        """Send a custom command to the device"""
        return self._send_mqtt_command(command)

# Create tool instance
tool = MQTTControlTool()

# Register tools with MCP server
@mcp_server.list_tools()
async def list_tools() -> list[types.Tool]:
    return [
        types.Tool(
            name="turn_on",
            description="Turn the relay ON.",
            inputSchema={"type": "object", "properties": {}}
        ),
        types.Tool(
            name="turn_off",
            description="Turn the relay OFF.",
            inputSchema={"type": "object", "properties": {}}
        ),
        types.Tool(
            name="send_custom_command",
            description="Send a custom command to the MQTT topic.",
            inputSchema={
                "type": "object",
                "properties": {"command": {"type": "string", "description": "Command to send"}},
                "required": ["command"]
            }
        )
    ]

@mcp_server.call_tool()
async def call_tool(name: str, arguments: dict) -> list[types.TextContent]:
    if name == "turn_on":
        result = tool.turn_on()
        return [types.TextContent(type="text", text=result)]
    elif name == "turn_off":
        result = tool.turn_off()
        return [types.TextContent(type="text", text=result)]
    elif name == "send_custom_command":
        command = arguments.get("command")
        if not command:
            return [types.TextContent(type="text", text="Error: Command parameter is required")]
        result = tool.send_custom_command(command)
        return [types.TextContent(type="text", text=result)]
    raise ValueError(f"Tool not found: {name}")

# SSE endpoint for MCP (basic connectivity)
async def sse_endpoint():
    async def event_generator():
        yield {"data": f'{{"type": "server_ready", "server": "MQTTControlServer"}}'}
        while True:
            await asyncio.sleep(1)
            yield {"data": '{"type": "ping"}'}
    return EventSourceResponse(event_generator())

# Tools list endpoint
@app.get("/mcp/tools")
async def get_tools():
    tools = await list_tools()
    return {"tools": [tool.dict() for tool in tools]}

# Tool call endpoint
class ToolCallRequest(BaseModel):
    name: str
    arguments: dict = {}

@app.post("/mcp/call_tool")
async def call_tool_endpoint(request: ToolCallRequest):
    try:
        result = await call_tool(request.name, request.arguments)
        return {"content": [content.dict() for content in result]}
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))

# Mount MCP endpoints
app.get("/mcp/sse")(sse_endpoint)

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)