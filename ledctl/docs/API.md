# LB3C LED Control System API Documentation

## Overview

The LB3C system provides both REST API and WebSocket interfaces for controlling LED hardware. All API endpoints are prefixed with `/api/v1/`.

## Authentication

API authentication can be enabled by setting `API_AUTH_ENABLED=True` in your `.env` file.

### Generating API Keys

```bash
python generate_api_key.py 2  # Generate 2 API keys
```

### Using API Keys

Include the API key in your requests using one of these methods:

1. **Header** (recommended):
   ```
   X-API-Key: your-api-key-here
   ```

2. **Query Parameter**:
   ```
   GET /api/v1/status?api_key=your-api-key-here
   ```

## Rate Limiting

All endpoints are rate-limited to prevent abuse:

- Default: 200 requests per hour
- File operations: 10 per hour
- Device switching: 30 per hour

Rate limit headers are included in responses:
- `X-RateLimit-Limit`: Maximum requests allowed
- `X-RateLimit-Remaining`: Requests remaining
- `X-RateLimit-Reset`: Unix timestamp when limit resets

## REST API Endpoints

### System Status

#### GET /api/v1/status
Get current system status.

**Rate Limit**: 60 per minute

**Response**:
```json
{
  "device": {
    "connected": true,
    "type": "HUB75",
    "dimensions": [64, 32]
  },
  "playback": {
    "is_playing": true,
    "current_animation": "rainbow.gif",
    "parameters": {
      "brightness": 0.8,
      "speed": 1.0,
      "gamma": 2.2,
      "rgb_balance": [1.0, 1.0, 1.0]
    }
  },
  "system": {
    "uptime": 3600,
    "version": "1.0.0",
    "environment": "production"
  }
}
```

### Device Control

#### GET /api/v1/device
Get current device information.

**Authentication**: Required

**Response**:
```json
{
  "type": "HUB75",
  "dimensions": [64, 32],
  "brightness": 0.8,
  "config": {
    "gpio_slowdown": 2,
    "pwm_bits": 11
  }
}
```

#### PUT /api/v1/device
Switch to a different LED device.

**Authentication**: Required  
**Rate Limit**: 30 per hour

**Request Body**:
```json
{
  "device_type": "HUB75",  // Required: HUB75, WS2811, WLED, MOCK
  "brightness": 0.8,       // Optional: 0.0-1.0
  "gamma": 2.2,           // Optional: 0.1-5.0
  "fps": 30               // Optional: 1-120
}
```

### Animation Control

#### POST /api/v1/animation
Control animation playback.

**Authentication**: Required  
**Rate Limit**: 30 per minute

**Request Body**:
```json
{
  "action": "play",        // Required: play, pause, stop, next, previous
  "filename": "fire.gif",  // Optional: for play action
  "loop": true,           // Optional: for play action
  "speed": 1.5            // Optional: 0.1-10.0
}
```

### Parameter Control

#### GET /api/v1/parameters
Get current playback parameters.

**Response**:
```json
{
  "brightness": 0.8,
  "speed": 1.0,
  "gamma": 2.2,
  "rgb_balance": [1.0, 1.0, 1.0]
}
```

#### PUT /api/v1/parameters
Update a playback parameter.

**Authentication**: Required  
**Rate Limit**: 60 per minute

**Request Body**:
```json
{
  "parameter": "brightness",  // Required: brightness, speed, gamma, rgb_balance
  "value": 0.5               // Required: value appropriate for parameter
}
```

### File Management

#### GET /api/v1/files
List uploaded animation files.

**Authentication**: Required  
**Rate Limit**: 100 per minute

**Response**:
```json
{
  "files": [
    {
      "name": "rainbow.gif",
      "size": 102400,
      "modified": 1701234567
    }
  ]
}
```

#### POST /api/v1/upload
Upload an animation file.

**Authentication**: Required  
**Rate Limit**: 10 per hour  
**Max File Size**: 100MB

**Request**: Multipart form data with `file` field

**Response**:
```json
{
  "success": true,
  "filename": "animation_1701234567.gif",
  "size": 102400
}
```

#### DELETE /api/v1/files/{filename}
Delete an uploaded file.

**Authentication**: Required  
**Rate Limit**: 30 per minute

### Health Check

#### GET /api/v1/health
Health check endpoint for monitoring.

**No authentication required**  
**No rate limiting**

**Response**:
```json
{
  "status": "healthy",      // healthy, degraded, unhealthy
  "device_connected": true,
  "timestamp": 1701234567
}
```

## WebSocket Events

Connect to the WebSocket endpoint at `/socket.io/`.

### Client to Server Events

#### play
Start animation playback.
```javascript
socket.emit('play', {
  filename: 'rainbow.gif',
  loop: true
});
```

#### stop
Stop animation playback.
```javascript
socket.emit('stop');
```

#### set_parameter
Update a playback parameter.
```javascript
socket.emit('set_parameter', {
  parameter: 'brightness',
  value: 0.8
});
```

#### switch_device
Switch to a different LED device.
```javascript
socket.emit('switch_device', {
  device_type: 'HUB75'
});
```

### Server to Client Events

#### connected
Emitted when client successfully connects.

#### playing
Emitted when animation starts playing.
```javascript
{
  filename: 'rainbow.gif'
}
```

#### stopped
Emitted when animation stops.

#### parameter_updated
Emitted when a parameter is updated.
```javascript
{
  parameter: 'brightness',
  value: 0.8
}
```

#### device_initialized
Emitted when device is successfully initialized.
```javascript
{
  type: 'HUB75',
  width: 64,
  height: 32
}
```

#### error
Emitted when an error occurs.
```javascript
{
  message: 'Device initialization failed',
  code: 'DEVICE_ERROR',
  details: {}
}
```

#### frame_info
Emitted periodically during playback.
```javascript
{
  frame: 42,
  total: 100,
  fps: 30
}
```

## Error Responses

All API errors follow this format:

```json
{
  "error": "Human-readable error message",
  "code": "ERROR_CODE",
  "details": {
    // Additional error context
  }
}
```

Common error codes:
- `VALIDATION_ERROR`: Input validation failed
- `AUTH_REQUIRED`: Authentication required
- `RATE_LIMIT`: Rate limit exceeded
- `DEVICE_ERROR`: Hardware device error
- `FILE_ERROR`: File processing error
- `NOT_FOUND`: Resource not found

## Security Headers

All API responses include security headers:
- `X-Content-Type-Options: nosniff`
- `X-Frame-Options: DENY`
- `X-XSS-Protection: 1; mode=block`
- `Referrer-Policy: strict-origin-when-cross-origin`

## CORS Configuration

CORS is configured via the `CORS_ORIGINS` environment variable. Set to `*` to allow all origins (not recommended for production).

## Example Usage

### cURL Examples

```bash
# Get system status
curl http://localhost:5000/api/v1/status

# Switch device (with API key)
curl -X PUT http://localhost:5000/api/v1/device \
  -H "X-API-Key: your-api-key" \
  -H "Content-Type: application/json" \
  -d '{"device_type": "HUB75"}'

# Upload file
curl -X POST http://localhost:5000/api/v1/upload \
  -H "X-API-Key: your-api-key" \
  -F "file=@animation.gif"
```

### JavaScript Example

```javascript
// REST API
const response = await fetch('/api/v1/status');
const status = await response.json();

// WebSocket
const socket = io();

socket.on('connect', () => {
  console.log('Connected to LED controller');
  
  socket.emit('play', {
    filename: 'rainbow.gif',
    loop: true
  });
});

socket.on('error', (error) => {
  console.error('LED Error:', error.message);
});
```