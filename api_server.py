"""
FastAPI server to bridge Python data providers with React frontend.
This lets us reuse ALL your existing Python code!
"""

from fastapi import FastAPI, WebSocket
from fastapi.middleware.cors import CORSMiddleware
from typing import Optional, Dict, Any
import asyncio
import json
from datetime import datetime

# Import your existing providers!
from core.data_provider import TickerDataProvider
from core.data_pipeline.base import DataManager
from core.data_pipeline.providers.alpaca_provider import AlpacaProvider

app = FastAPI()

# Enable CORS for Electron app
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize your existing providers
data_provider = TickerDataProvider()
data_manager = DataManager()

# Store active WebSocket connections
active_connections: Dict[str, WebSocket] = {}

@app.get("/api/quote/{symbol}")
async def get_quote(symbol: str):
    """Get quote data using your existing provider."""
    try:
        snapshot = data_provider.fetch_snapshot_payload(symbol)
        return snapshot
    except Exception as e:
        return {"error": str(e)}

@app.get("/api/chart/{symbol}")
async def get_chart_data(symbol: str, interval: str = "1D"):
    """Get chart data."""
    try:
        bars = data_provider.fetch_bars(symbol, interval)
        return {"bars": bars}
    except Exception as e:
        return {"error": str(e)}

@app.get("/api/news/{symbol}")
async def get_news(symbol: str):
    """Get news using your existing provider."""
    try:
        news = data_provider.fetch_news(symbol)
        return {"news": news}
    except Exception as e:
        return {"error": str(e)}

@app.get("/api/fundamentals/{symbol}")
async def get_fundamentals(symbol: str):
    """Get fundamentals data."""
    try:
        fundamentals = data_provider.fetch_fundamentals(symbol)
        return fundamentals
    except Exception as e:
        return {"error": str(e)}

@app.websocket("/ws/{client_id}")
async def websocket_endpoint(websocket: WebSocket, client_id: str):
    """WebSocket for real-time data."""
    await websocket.accept()
    active_connections[client_id] = websocket

    try:
        while True:
            # Receive message from client
            data = await websocket.receive_text()
            message = json.loads(data)

            if message["type"] == "subscribe":
                symbol = message["symbol"]
                # Start streaming data for this symbol
                await stream_symbol_data(websocket, symbol)

    except Exception as e:
        print(f"WebSocket error: {e}")
    finally:
        del active_connections[client_id]

async def stream_symbol_data(websocket: WebSocket, symbol: str):
    """Stream real-time data for a symbol."""
    while True:
        try:
            # Get latest data
            quote = data_provider.fetch_snapshot_payload(symbol)

            # Send to client
            await websocket.send_json({
                "type": "quote",
                "symbol": symbol,
                "data": quote,
                "timestamp": datetime.now().isoformat()
            })

            # Wait before next update
            await asyncio.sleep(1)  # 1 second updates

        except Exception as e:
            print(f"Stream error: {e}")
            break

if __name__ == "__main__":
    import uvicorn
    print("Starting Mira API Server on http://localhost:8000")
    print("All your Python data providers are now available to React!")
    uvicorn.run(app, host="0.0.0.0", port=8000)