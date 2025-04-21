# BookVerse

BookVerse is a web-based digital book reading and sharing platform that allows users to browse, read, and discuss books. It provides separate interfaces for readers, authors, and administrators.

## Features

- **User Authentication**: Register and login as reader, author, or admin
- **Browse Books**: Discover and search for books in the library
- **Reading Experience**: Read books directly in the browser
- **User Library**: Save books to your personal library
- **Reviews**: Rate and review books
- **Dark/Light Mode**: Toggle between dark and light themes
- **Responsive Design**: Works on desktop and mobile devices

## Technology Stack

- **Backend**: Flask, SQLAlchemy
- **Frontend**: HTML, CSS, JavaScript, Bootstrap 5
- **Database**: SQLite (development), PostgreSQL (production)
- **Authentication**: Flask-Login
- **Image Processing**: Pillow

## Setup Instructions

1. Clone the repository:
   ```
   git clone https://your-repo-url/bookverse.git
   cd bookverse
   ```

2. Create and activate a virtual environment:
   ```
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. Install dependencies:
   ```
   pip install -r requirements.txt
   ```

4. Run the application:
   ```
   python app.py
   ```

5. Open your browser and navigate to `http://127.0.0.1:5000`

## Deployment on Render

1. Create a new Web Service on Render
2. Connect your GitHub repository
3. Use the following settings:
   - **Build Command**: `pip install -r requirements.txt`
   - **Start Command**: `gunicorn app:app`
   - **Environment Variables**:
     - `SECRET_KEY`: your-secret-key
     - `DATABASE_URL`: your-database-url (for PostgreSQL)

## Converting from Desktop App

This web application was converted from a desktop Tkinter application. The conversion involved:

1. Replacing Tkinter UI with HTML/CSS/JavaScript
2. Creating a client-server architecture with Flask
3. Adapting the database interactions for web context
4. Recreating the cozy corner image generation for web display

## Default Accounts

For testing purposes, the application comes with three default accounts:

1. **Admin**
   - Email: admin@bookverse.com
   - Password: admin123

2. **Author**
   - Email: author@bookverse.com
   - Password: author123

3. **Reader**
   - Email: reader@bookverse.com
   - Password: reader123

## License

[MIT License](LICENSE) 