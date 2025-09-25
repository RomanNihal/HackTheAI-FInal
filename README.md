#  Smart Triage AI

**Smart Triage AI** is a full-stack web application developed for the HackTheAI hackathon. It serves as an intelligent assistant for customer support teams, using a multi-step AI workflow to automatically analyze, categorize, and prioritize incoming support tickets.

## ✨ Features

* **AI-Powered Ticket Analysis:** Utilizes a SmythOS AI agent to perform Natural Language Processing (NLP) to determine a ticket's **category** (e.g., Hardware, Billing) and **sentiment**.
* **Intelligent Prioritization:** A custom rules engine automatically assigns a **priority** (High, Medium, Low) based on the AI analysis.
* **User & Ticket Management:** A complete system for user registration and authenticated ticket submission, with all data stored persistently in a **SQLite database**.
* **Live Admin Dashboard:** A dynamic dashboard that displays all tickets in real-time, allows admins to update ticket statuses, and shows live statistics.
* **On-the-Fly Statistics:** An API endpoint that provides judges with real-time statistics on tickets created and solved within the last hour.

## 🛠️ Tech Stack

| Category      | Technology                               |
| ------------- | ---------------------------------------- |
| **Backend** | Python, FastAPI, Uvicorn                 |
| **Database** | SQLite                                   |
| **AI Engine** | SmythOS Flow Builder                     |
| **Frontend** | HTML, CSS, JavaScript, Bootstrap 5       |




# API Documentation

This documentation provides details on the available endpoints for the **Smart Triage** backend API.

## Endpoints
---
### `POST /register`
Registers a new user in the system.

**Request Body:** `application/json`
| Field | Type   | Required | Description                |
| :---- | :----- | :------- | :------------------------- |
| name  | string | Yes      | The full name of the user. |
| email | string | Yes      | The user's unique email.   |

---
### `POST /submit-ticket`
Submits a new support ticket for an existing user.

**Request Body:** `multipart/form-data`
| Field        | Type    | Required | Description                               |
| :----------- | :------ | :------- | :---------------------------------------- |
| user_id      | integer | Yes      | The ID of the user submitting the ticket. |
| ticket_text  | string  | Yes      | A detailed description of the issue.      |
| ticket_image | file    | No       | An optional image of the issue.           |

---
### `GET /tickets`
Retrieves a list of all support tickets currently in the system, joined with user and AI analysis data.

---
### `PUT /tickets/{ticket_id}/status`
Updates the status of a specific ticket.

**Path Parameter:**
| Parameter   | Type    | Description                     |
| :---------- | :------ | :------------------------------ |
| `ticket_id` | integer | The ID of the ticket to update. |

**Request Body:** `application/json`
| Field  | Type   | Required | Description                                     |
| :----- | :----- | :------- | :---------------------------------------------- |
| status | string | Yes      | The new status (e.g., "In Progress", "Closed"). |

---
### `GET /stats/last-hour`
Retrieves live statistics on tickets recorded and solved within the last hour.

---
### `GET /`
A root endpoint to confirm that the server is running.


# Setup and Installation

Follow these steps to run the project locally.

## Prerequisites
* Python 3.8+
* `pip` package manager
* VS Code with the **Live Server** extension is recommended for the frontend.

## Clone & Setup

```bash
# Clone the repository
git clone <repo-url>

# Navigate into the project directory
cd <project-folder-name>

# Create and activate a Python virtual environment
python -m venv venv
# On Windows, activate with: venv\Scripts\activate
# On macOS/Linux, activate with: source venv/bin/activate

# Install all the required dependencies
pip install -r requirements.txt


## 🚀 Running the Application

### Start the Backend Server:

In your terminal (with the virtual environment activated), run the following command:

```bash
uvicorn main:app --reload

### Run the Frontend:

1. In VS Code, right-click on the `.html` file.
2. Select **"Open with Live Server"**.
```

The backend API will now be running at: http://127.0.0.1:8000


##  Usage Workflow

### 📝 Register:
Go to the `register.html` page in your browser to create a new user.  
➡️ You will receive a **User ID**.

### 📩 Submit:
Go to the `index.html` page to submit a new support ticket.  
➡️ You must provide the **User ID** you received.

### 📊 View & Manage:
Go to the `dashboard.html` page to see all submitted tickets in a live-updating table.  
➡️ From here, you can also **change the status** of any ticket.


# Future Work

- **Full User Authentication**: Implement a proper login system with passwords and JWT (JSON Web Tokens).

- **Email Notifications**: Automatically send email alerts to support agents when a new "High" priority ticket is created.

- **Hospital Triage System**: Adapt the core engine for a healthcare use case to triage patient injuries based on images and descriptions, routing them to the correct specialist.
