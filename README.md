# The Agora: A Modern Hub for Real-Time Consensus
In ancient Greece, the Agora was the central public square—a vibrant, open hub for assembly, civic discourse, democratic voting, and commerce. This project, The Agora, reimagines that concept as a robust, scalable, and real-time online polling system.

It serves as a backend-focused implementation for the ProDev BE case study, meticulously engineered to handle high-frequency operations, real-time data processing, and a scalable API-first architecture.

## Key Features
| Feature                     | Description                                                                        |
|-----------------------------|------------------------------------------------------------------------------------|
| Real-Time Polling           | Enables users to create and participate in polls with instant updates.             |
| Scalable Architecture       | Built to efficiently manage increasing loads and user traffic.                     |
| API-First Design            | Provides a comprehensive RESTful API for seamless integration with other services. |
| Robust Data Handling        | Utilizes efficient data storage and retrieval mechanisms to ensure performance.    |
| Security                    | Implements best practices for data integrity and user authentication.              |
| Extensibility               | Modular design allows for easy addition of new features and modifications.         |
| Comprehensive Documentation | Offers clear and detailed documentation for developers and users.                  |
| Testing Suite               | Includes unit and integration tests to ensure reliability and stability.           |
| Secure Payment Integration  | Integrates with Chapa payment gateway for monetized polling features.              |
| Asynchronous Task Handling  | Uses Celery for managing background tasks and real-time updates.                   |
| Payment Invoice Generation  | Automatically generates and sends payment invoices upon successful transactions.   |
 | Poll Categorization         | Supports categorization of polls for better organization and retrieval.            |
| User Management             | Features user registration, authentication, and profile management.                |
| Poll Scheduling             | Allows scheduling of polls to open and close at specified times.                   |
| Poll Voting Restrictions    | Supports various voting restrictions (e.g., one vote per user, IP-based limits).   |

## Technology Stack
| Component               | Technology         |
|-------------------------|--------------------|
| Backend                 | Python with Django |
| Database                | PostgreSQL         |
| Real-Time Communication | WebSockets         |
| Containerization        | Docker             |
| Version Control         | Git and GitHub     |
| CI/CD                   | GitHub Actions     |
| Testing                 | PyTest             |
| API Documentation       | Swagger / OpenAPI  |
| Deployment              | Heroku             |
| Formatting/Linting      | Ruff / Black       |
| Code Quality            | SonarCloud         |
| Asynchronous Tasks      | Celery             |
| Message Broker          | Redis              |
| Payment Gateway         | Chapa              |
| Task Scheduling         | Django Celery Beat |

## Getting Started
To get started with The Agora, follow these steps:
1. **Clone the Repository**:
   ```bash
   git clone <repository_url>
   cd alx-project-nexus
   ```
2. **Set Up the Environment**:
   - Install Python 3.10+ and PostgreSQL.
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
   - Create a PostgreSQL database and update the `settings.py` with your database credentials. (see the .env.example file for reference)
   
4. **Run Migrations**:
   ```bash
   ## Apply database migrations
   python manage.py migrate
   
   ## Collect static files
   python manage.py collectstatic
   ```
5. **Start the Development Server**:
   ```bash
   ## Run command to initialize Categories
   python manage.py initialize_poll_categories
   
   ## Start Redis Server in another terminal:
   redis-server
   
   ## or use Docker to start Redis:
   docker run -d -p 6379:6379 redis
   
   ## Start Celery Worker in another terminal:
   celery -A core worker --loglevel=info --pool=solo
   
   ## Start the Celery Beat Scheduler in another terminal:
   celery -A core beat --loglevel=info --scheduler django_celery_beat.schedulers:DatabaseScheduler
   
   ## Finally, start the Django development server:
   python manage.py runserver
   ```
6. **Access the Application**:
    ```bash
    ## Visit the application
    Open your web browser and navigate to `http://localhost:8000/`.
   
    ## Swagger API Documentation
    Access the API documentation at `http://localhost:8000/api/v1/docs/`
    ```

7. **Run Tests**:
   ```bash
    ## Execute the test suite
    pytest
   
    ## Test Coverage Report
    coverage run manage.py test
   ```

## API Documentation
| Endpoint                                 | Method | Description                                 |
|------------------------------------------|--------|---------------------------------------------|
| Poll Management                          |        |                                             |
| `/api/v1/polls/`                         | GET    | Retrieve a list of all polls                |
| `/api/v1/polls/`                         | POST   | Create a new poll                           |
| `/api/v1/polls/{poll_id}/`               | GET    | Retrieve details of a specific poll         |
| `/api/v1/polls/{poll_id}/`               | PATCH  | Update a specific poll                      |
| `/api/v1/polls/{poll_id}/`               | DELETE | Delete a specific poll                      |
| `/api/v1/polls/{poll_id}/close/`         | POST   | Close voting for a specific poll            |
| Vote on Polls                            |        |                                             |
| `/api/v1/polls/{poll_id}/vote/`          | POST   | Cast a vote for a specific poll             |
| User Management                          |        |                                             |
| `/api/v1/auth/register/`                 | POST   | Register a new user                         |
| `/api/v1/auth/login/`                    | POST   | User login                                  |
| `/api/v1/auth/logout/`                   | POST   | User logout                                 |
| `/api/v1/auth/verify-email/`             | GET    | Verify user email                           |
| `/api/v1/users/resend-verification/`     | POST   | Resend email verification                   |
| Real-Time Updates                        |        |                                             |
| `ws://127.0.0.1:8000/ws/poll/{poll_id}/` | WS     | WebSocket endpoint for real-time updates    |
| Organizational Management                |        |                                             |
| `/api/v1/organizations/`                 | GET    | Retrieve a list of organizations            |
| `/api/v1/organizations/`                 | POST   | Create a new organization                   |
| `/api/v1/organizations/{org_id}/`        | GET    | Retrieve details of a specific organization |
| `/api/v1/organizations/{org_id}/`        | PATCH  | Update a specific organization              |
| `/api/v1/organizations/{org_id}/`        | DELETE | Delete a specific organization              |
| Payment Integration                      |        |                                             |
| `/api/v1/payments/initialize/`           | POST   | Initialize Payment                          |
| `/api/v1/payments/verify/`               | POST   | Verify Payment                              |
| `/api/v1/payments/{payment_id}/`         | GET    | Retrieve Payment Details                    |

## API Usage Examples
### Creating a Poll
```bash
curl -X POST http://localhost:8000/api/v1/polls/ \
-H "Content-Type: application/json" \
-d '{
    "poll_question": "Which framework do you prefer?",
    "poll_category": 1,
    "start_date": "2025-11-25T12:00:00Z",
    "end_date": "2025-12-01T12:00:00Z",
    "is_public": true,
    "options": [
        { "text": "Django" },
        { "text": "FastAPI" },
        { "text": "Flask" },
        { "text": "Spring Boot" }
    ]
}'
```
### Voting on a Poll
```bash
curl -X POST http://localhost:8000/api/v1/polls/{poll_id}/vote/ \
-H "Content-Type: application/json" \
-d '{
    "option_id": 3
}'
```
### User Registration
```bash
curl -X POST http://localhost:8000/api/v1/auth/register/ \
-H "Content-Type: application/json" \
-d '{
    "email": "newuser",
    "password": "securepassword",
    "confirm_password": "securepassword",
    "first_name": "New",
    "last_name": "User",
    "phone_number": "1234567890"
}'
```
### User Login
```bash
curl -X POST http://localhost:8000/api/v1/auth/login/ \
-H "Content-Type: application/json" \
-d '{
    "email": "newuser",
    "password": "securepassword"
}'
```

### Registering an Organization
```bash
curl -X POST http://localhost:8000/api/v1/organizations/ \
-H "Content-Type: application/json" \
-d '{
  "org_name": "Arise Foundation Nigeria",
  "org_description": "Arise Foundation is a Non-governmental Organization that is dedicated to building a more united society with inclusivity of race, gender and status.",
  "org_url": "https://arise.org",
  "org_email": "test@organization.com"
}'
```

### Invitation to Join an Organization
```bash
curl -X POST http://localhost:8000/api/v1/organizations/{org_id}/invite/ \
-H "Content-Type: application/json" \
-d '{
  "email": "test-user@organization.com"
}'
```

### Join an Organization via Invitation
```bash
curl -X POST http://localhost:8000/api/v1/organizations/join/ \
-H "Content-Type: application/json" \
-d '{
  "token": "your-invitation-token-here"
}'
```

### Initialize Payment
```bash
curl -X POST http://localhost:8000/api/v1/payments/initialize/ \
-H "Content-Type: application/json" \
-d '{
  "return_url": "https://6826d4eb58e1.ngrok-free.app/api/v1/payments/verify/"
}'
```

### Verify Payment
```bash
curl -X GET http://localhost:8000/api/v1/payments/verify/?tx_ref=your_transaction_id_here
```