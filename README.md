# CytoLens API

A high-performance FastAPI-based backend service for managing and analyzing Whole Slide Images (WSI) in digital pathology. This API provides comprehensive functionality for slide management, AI-powered inference, and real-time visualization of pathology images.

## 🔬 Overview

CytoLens API is a professional-grade backend service designed to handle large-scale pathology image processing with AI inference capabilities. It features:

- **WSI Management**: Upload, store, and manage whole slide images with S3 integration
- **AI Inference**: Integration with external inference services for automated pathology analysis
- **Real-time Visualization**: Deep Zoom Image (DZI) tile serving for OpenSeadragon viewers
- **Robust Authentication**: Dual authentication system with JWT cookies and API keys
- **Task Tracking**: Comprehensive task management for long-running inference operations

## 🚀 Features

### Core Functionality
- **Multi-part Upload System**: Handle large WSI files (up to 50GB) with resumable uploads
- **S3 Integration**: Automatic storage management with AWS S3
- **PostgreSQL Database**: Robust data persistence with SQLAlchemy ORM
- **Real-time Webhooks**: Asynchronous status updates from inference services
- **Bulk Operations**: Efficient batch processing for slide management

### Security Features
- JWT-based authentication with secure HTTP-only cookies
- API key generation for programmatic access
- CSRF protection for web sessions
- Password hashing with bcrypt
- Role-based access control

### Performance Optimizations
- Connection pooling for database operations
- Efficient tile caching for image serving
- Pagination support for large datasets
- Concurrent request handling with async/await

## 📋 Prerequisites

### Core Requirements
- Python 3.11.13
- PostgreSQL database
- AWS S3 bucket (for slide storage)
- External inference service (optional, for AI analysis)

### For GPU Acceleration
- CUDA 12.2+ compatible NVIDIA GPU
- NVIDIA drivers (535.104.05 or later)
- cuDNN 8.9+
- CUDA Toolkit 12.2+

## 🛠️ Installation

### Option 1: Local Installation with Conda

#### 1. Clone the Repository
```bash
git clone https://github.com/yourusername/cytolens_api.git
cd cytolens_api
```

#### 2. Create Conda Environment
```bash
conda create -n cytolens python=3.11.13
conda activate cytolens
```

#### 3. Install Dependencies
```bash
pip install -r requirements.txt
```

### Option 2: Docker Installation (GPU Support)

#### 1. Prerequisites
- Docker Engine
- NVIDIA Container Toolkit (for GPU support)
- CUDA 12.2+ compatible GPU

#### 2. Build Docker Image
```bash
docker build -t cytolens-api .
```

#### 3. Run Container
```bash
docker run --gpus all \
  -p 5000:5000 \
  -v /path/to/slides:/mnt/nvme_gds/slides \
  -v /path/to/predictions:/mnt/nvme_gds/predictions \
  --env-file .env \
  cytolens-api
```

### Configure Environment Variables
Copy the example environment file and update with your settings:
```bash
cp .env.example .env
```

Edit `.env` with your configuration:
```env
# API Settings
API_VERSION=v1
ENVIRONMENT=local
DEBUG=false

# Database Settings
POSTGRES_USER=your_db_user
POSTGRES_PASSWORD=your_db_password
POSTGRES_DB=cytolens_db

# JWT Settings
JWT_SECRET_KEY=your-secret-key-here-change-this-in-production
JWT_ALGORITHM=HS256
JWT_ACCESS_TOKEN_EXPIRE_MINUTES=30

# AWS Settings
AWS_ACCESS_KEY_ID=your_aws_access_key
AWS_SECRET_ACCESS_KEY=your_aws_secret_key

# S3 Settings
S3_BUCKET_NAME=your_s3_bucket
S3_SLIDE_FOLDER=slides
S3_TEMP_SLIDE_FOLDER=temp_slides
S3_RESULTS_FOLDER=results

# Local Storage Settings
SLIDE_DIR=/mnt/nvme_gds/slides
PREDICTION_DIR=/mnt/nvme_gds/predictions

# Inference Service Settings
INFERENCE_SERVICE_URL=http://localhost:8000
INFERENCE_API_KEY=your_inference_api_key
```

### Initialize Database
The database tables will be automatically created on first run through SQLAlchemy.

### Run the Application

#### Local Installation
```bash
python main.py
```

The API will be available at `http://localhost:5000`

## 📚 API Documentation

Once running, access the interactive API documentation at:
- Swagger UI: `http://localhost:5000/docs`
- ReDoc: `http://localhost:5000/redoc`

### Main API Endpoints

#### Authentication
- `POST /auth/register` - Register new user
- `POST /auth/login` - User login
- `POST /auth/logout` - User logout
- `POST /auth/api-keys` - Generate API key

#### Slides Management
- `GET /slides` - List user's slides
- `GET /slides/{slide_id}` - Get slide details
- `POST /slides/upload/start` - Start multipart upload
- `POST /slides/upload/finish` - Complete upload
- `DELETE /slides/{slide_id}` - Delete slide
- `PATCH /slides/{slide_id}` - Update slide name
- `POST /slides/bulk-delete` - Delete multiple slides

#### Inference
- `POST /inference` - Start inference task
- `GET /inference/tasks` - List inference tasks
- `GET /inference/tasks/{task_id}` - Get task status
- `DELETE /inference/tasks/{task_id}` - Cancel task

#### Viewer
- `GET /viewer/{slide_id}.dzi` - Get DZI descriptor
- `GET /viewer/{slide_id}_files/{level}/{col}_{row}.jpg` - Get image tile
- `GET /viewer/predictions/{slide_id}` - Get predictions

## 🗄️ Database Schema

### Core Models

#### User
- `id`: Primary key
- `username`: Unique username
- `password_hash`: Bcrypt hashed password
- `role`: User role (default: "user")

#### Slide
- `id`: Primary key
- `name`: Slide name
- `owner_id`: Foreign key to User
- `model_id`: Foreign key to Model
- `original_filename`: Original file name
- `type`: Slide type
- `created_at`: Creation timestamp

#### InferenceTask
- `id`: Primary key
- `inference_task_id`: External task ID
- `slide_id`: Foreign key to Slide (cascade delete)
- `user_id`: Foreign key to User
- `state`: Task state (PENDING, STARTED, SUCCESS, FAILURE)
- `confidence`: Confidence threshold
- `created_at`: Creation timestamp
- `completed_at`: Completion timestamp
- `message`: Status message

#### ApiKey
- `id`: Primary key
- `user_id`: Foreign key to User
- `key`: SHA256 hashed API key
- `name`: User-defined label
- `created_at`: Creation timestamp
- `expires_at`: Expiration timestamp (optional)

## 🔧 Configuration

### File Upload Limits
- Minimum file size: 1MB
- Maximum file size: 50GB
- Allowed extensions: `.svs`

### Viewer Settings
- Tile size: 512x512 pixels
- Tile format: JPEG
- Deep Zoom Image (DZI) protocol support

### Performance Tuning
- Database connection pooling with 1-hour recycle
- Configurable JWT token expiration
- Adjustable tile cache settings

## 🔒 Authentication

### Cookie-based Authentication (Web)
```javascript
// Login and receive cookies automatically
const response = await fetch('/auth/login', {
  method: 'POST',
  credentials: 'include',
  body: JSON.stringify({ username, password })
});
```

### API Key Authentication (Programmatic)
```python
import requests

headers = {
    'Authorization': 'Bearer your-api-key-here'
}
response = requests.get('http://localhost:5000/slides', headers=headers)
```

## 🚢 Deployment

### Docker Support
The application supports Docker deployment with the `ENVIRONMENT=docker` setting, which automatically adjusts database host configuration.

### Production Considerations
1. Use a strong `JWT_SECRET_KEY`
2. Enable HTTPS in production
3. Configure CORS appropriately
4. Set `DEBUG=false`
5. Use environment-specific S3 buckets
6. Implement rate limiting
7. Set up monitoring and logging

## 📦 Dependencies

### Core Dependencies
- **fastapi**: Modern web framework for building APIs
- **uvicorn**: Lightning-fast ASGI server
- **sqlalchemy**: SQL toolkit and ORM
- **pydantic**: Data validation using Python type annotations
- **python-jose**: JWT implementation
- **passlib[bcrypt]**: Password hashing
- **psycopg2-binary**: PostgreSQL adapter
- **httpx**: Async HTTP client
- **boto3**: AWS SDK for S3 operations
- **openai**: OpenAI API integration

### GPU-Accelerated Libraries
- **cucim**: GPU-accelerated image I/O and processing
- **cupy**: GPU array computing with CUDA
- **nvjpeg**: NVIDIA JPEG decoder

## 🧪 Testing

Run tests with:
```bash
pytest tests/
```

## 📊 Project Structure

```
cytolens_api/
├── api/
│   ├── dependencies/     # Authentication and security
│   ├── routes/           # API endpoints
│   ├── schemas/          # Pydantic models
│   └── services/         # Business logic
├── core/
│   ├── config.py         # Application settings
│   └── constants.py      # Application constants
├── utils/
│   ├── aws_utils.py      # S3 operations
│   ├── jwt_utils.py      # JWT handling
│   ├── password_utils.py # Password hashing
│   ├── postgres_utils.py # Database models
│   └── slide_utils.py    # Slide processing
├── main.py               # Application entry point
├── requirements.txt      # Python dependencies
└── .env.example         # Environment template
```

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## 📝 License

This project is licensed under the MIT License - see the LICENSE file for details.

## 🆘 Support

For issues and questions:
- Open an issue on GitHub
- Contact the development team
- Check the API documentation at `/docs`

## 🔄 Webhook Integration

The API supports webhook callbacks from external inference services. Configure your inference service to send POST requests to:
```
POST /inference/webhook/callback
Headers: X-API-Key: your-inference-api-key
```

## 🎯 Roadmap

- [ ] Add support for additional WSI formats (.ndpi, .mrxs)
- [ ] Implement caching layer with Redis
- [ ] Add real-time notifications via WebSocket
- [ ] Expand AI model integration options
- [ ] Implement advanced search and filtering
- [ ] Add batch inference processing
- [ ] Create admin dashboard
- [ ] Implement audit logging

## ⚠️ Important Notes

- Ensure PostgreSQL is running before starting the application
- S3 bucket must have appropriate permissions for multipart uploads
- Large WSI files may require adjusted timeout settings
- The inference service URL must be accessible from the API server

---

Built with ❤️ for digital pathology research and clinical applications