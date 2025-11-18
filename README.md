# The Agora: A Modern Hub for Real-Time Consensus
In ancient Greece, the Agora was the central public square—a vibrant, open hub for assembly, civic discourse, democratic voting, and commerce. This project, The Agora, reimagines that concept as a robust, scalable, and real-time online polling system.

It serves as a backend-focused implementation for the ProDev BE case study, meticulously engineered to handle high-frequency operations, real-time data processing, and a scalable API-first architecture.

## Key Features
- **Real-Time Polling**: Supports high-frequency voting with real-time updates.
- **Scalable Architecture**: Designed to handle increasing loads seamlessly.
- **API-First Design**: Comprehensive RESTful API for easy integration.
- **Robust Data Handling**: Efficient data storage and retrieval mechanisms.
- **Security**: Implements best practices for data integrity and user authentication.
- **Extensibility**: Modular design allows for easy feature additions and modifications.
- **Comprehensive Documentation**: Clear and detailed documentation for developers and users.
- **Testing Suite**: Includes unit and integration tests to ensure reliability.

## Technology Stack
- **Backend**: Python with Django
- **Database**: PostgreSQL
- **Real-Time Communication**: WebSockets
- **Containerization**: Docker
- **Version Control**: Git and GitHub
- **CI/CD**: GitHub Actions
- **Testing**: PyTest
- **API Documentation**: Swagger / OpenAPI
- **Deployment**: AWS / Heroku
- **Formatting/Linting**: Ruff
- **Code Quality**: SonarCloud
- **Celery**: For handling asynchronous tasks
- **Redis**: As a message broker for Celery

## Getting Started
To get started with The Agora, follow these steps:
1. **Clone the Repository**:
   ```bash
   git clone <repository_url>
   cd alx-project-nexus
   ```
2. **Set Up the Environment**:
   - Install Python 3.8+ and PostgreSQL.
   - Create a virtual environment and activate it:
     ```bash
     python -m venv venv
     source venv/bin/activate  # On Windows use `venv\Scripts\activate`
     ```
   - Install the required dependencies:
     ```bash
     pip install -r requirements.txt
     ```
3. **Configure the Database**:
   - Create a PostgreSQL database and update the `settings.py` with your database credentials.
4. **Run Migrations**:
   ```bash
   python manage.py migrate
   ```
5. **Start the Development Server**:
   ```bash
   python manage.py runserver
   
   ## Start Redis Server in another terminal:
   redis-server
   
   ## Using Docker to start Redis:
   docker run -d -p 6379:6379 redis
   
   ## Start Celery Worker in another terminal:
   celery -A core worker --loglevel=info --pool=solo
   ```
6. **Access the Application**:
   Open your web browser and navigate to `http://localhost:8000`.
7. **Run Tests**:
   ```bash
   pytest
   ```
8. **Lint the Code**:
   ```bash
   ruff format . (This will reformat all your files to match the style rules.)
   ruff check . (This will check all files and report any errors)
   ruff check . --fix (This will fix import sorting, remove unused imports, etc.)
   ```