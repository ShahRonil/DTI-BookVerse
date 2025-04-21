import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import sqlite3
import hashlib
import os
import io
import base64
import threading
from datetime import datetime
from PIL import Image, ImageTk, ImageDraw, ImageFilter, ImageOps
import PyPDF2
import webbrowser
import ttkbootstrap as tb
from ttkbootstrap.constants import *
from ttkbootstrap.toast import ToastNotification
import math
import random

# Create assets directory if it doesn't exist
if not os.path.exists('assets'):
    os.makedirs('assets')

class Database:
    def __init__(self):
        database_file = 'bookverse.db'
        # Connect to the database
        self.conn = sqlite3.connect(database_file)
        self.cursor = self.conn.cursor()
        
        # Initialize database tables
        self.initialize_db()
        self.migrate_db()
        
        # Add sample books if database is empty
        self.add_sample_books()
        
    def migrate_db(self):
        """Handle database migrations for schema updates"""
        try:
            # Check if pdf_data column exists in books table
            self.cursor.execute("SELECT pdf_data FROM books LIMIT 1")
        except sqlite3.OperationalError:
            # Column doesn't exist, perform migration
            print("Migrating database schema...")
            
            # Create temporary table with new schema
            self.cursor.execute('''
                CREATE TABLE IF NOT EXISTS books_new (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    title TEXT NOT NULL,
                    author_email TEXT NOT NULL,
                    description TEXT,
                    pdf_data BLOB NOT NULL,
                    amazon_link TEXT,
                    upload_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (author_email) REFERENCES users(email)
                )
            ''')
            
            try:
                # Copy data from old table to new table
                self.cursor.execute('''
                    INSERT INTO books_new (id, title, author_email, description, amazon_link, upload_date)
                    SELECT id, title, author_email, description, amazon_link, upload_date
                    FROM books
                ''')
                
                # Drop old table
                self.cursor.execute('DROP TABLE books')
                
                # Rename new table to books
                self.cursor.execute('ALTER TABLE books_new RENAME TO books')
                
                self.conn.commit()
                print("Database migration completed successfully")
                
            except Exception as e:
                print(f"Migration error: {str(e)}")
                self.conn.rollback()
                # If migration fails, create fresh books table
                self.cursor.execute('DROP TABLE IF EXISTS books_new')
                self.cursor.execute('''
                    CREATE TABLE IF NOT EXISTS books (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        title TEXT NOT NULL,
                        author_email TEXT NOT NULL,
                        description TEXT,
                        pdf_data BLOB NOT NULL,
                        amazon_link TEXT,
                        upload_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        FOREIGN KEY (author_email) REFERENCES users(email)
                    )
                ''')
                self.conn.commit()
                print("Created fresh books table with new schema")

        try:
            # Check if date_of_birth column exists in users table
            self.cursor.execute("SELECT date_of_birth FROM users LIMIT 1")
        except sqlite3.OperationalError:
            # Column doesn't exist, perform migration
            print("Migrating users table schema...")
            
            # Create temporary table with new schema
            self.cursor.execute('''
                CREATE TABLE IF NOT EXISTS users_new (
                    email TEXT PRIMARY KEY,
                    username TEXT NOT NULL,
                    password TEXT NOT NULL,
                    full_name TEXT,
                    user_type TEXT NOT NULL,
                    date_of_birth DATE,
                    gender TEXT,
                    book_genre_preference TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    avatar BLOB,
                    reading_streak INTEGER DEFAULT 0,
                    books_read INTEGER DEFAULT 0
                )
            ''')
            
            try:
                # Copy data from old table to new table
                self.cursor.execute('''
                    INSERT INTO users_new (email, username, password, full_name, user_type, date_of_birth, gender, book_genre_preference, created_at)
                    SELECT email, username, password, full_name, user_type, date_of_birth, gender, book_genre_preference, created_at
                    FROM users
                ''')
                
                # Drop old table
                self.cursor.execute('DROP TABLE users')
                
                # Rename new table to users
                self.cursor.execute('ALTER TABLE users_new RENAME TO users')
                
                self.conn.commit()
                print("Users table migration completed successfully")
                
            except Exception as e:
                print(f"Users table migration error: {str(e)}")
                self.conn.rollback()
                # If migration fails, create fresh users table
                self.cursor.execute('DROP TABLE IF EXISTS users_new')
                self.cursor.execute('''
                    CREATE TABLE IF NOT EXISTS users (
                        email TEXT PRIMARY KEY,
                        username TEXT NOT NULL,
                        password TEXT NOT NULL,
                        full_name TEXT,
                        user_type TEXT NOT NULL,
                        date_of_birth DATE,
                        gender TEXT,
                        book_genre_preference TEXT,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        avatar BLOB,
                        reading_streak INTEGER DEFAULT 0,
                        books_read INTEGER DEFAULT 0
                    )
                ''')
                self.conn.commit()
                print("Created fresh users table with new schema")

        # Add badges table if it doesn't exist
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS user_badges (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_email TEXT NOT NULL,
                badge_type TEXT NOT NULL,
                badge_name TEXT NOT NULL,
                date_earned TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_email) REFERENCES users(email)
            )
        ''')
        self.conn.commit()

    def initialize_db(self):
        # Users table
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS users (
                email TEXT PRIMARY KEY,
                username TEXT NOT NULL,
                password TEXT NOT NULL,
                full_name TEXT,
                user_type TEXT NOT NULL,
                date_of_birth DATE,
                gender TEXT,
                book_genre_preference TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                avatar BLOB,
                reading_streak INTEGER DEFAULT 0,
                books_read INTEGER DEFAULT 0
            )
        ''')
        
        # Books table
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS books (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL,
                description TEXT,
                author_email TEXT NOT NULL,
                amazon_link TEXT,
                pdf_data BLOB,
                upload_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (author_email) REFERENCES users(email)
            )
        ''')
        
        # Reviews table
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS reviews (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                book_id INTEGER NOT NULL,
                user_email TEXT NOT NULL,
                rating INTEGER NOT NULL,
                comment TEXT,
                review_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (book_id) REFERENCES books(id),
                FOREIGN KEY (user_email) REFERENCES users(email)
            )
        ''')
        
        # Discussions table
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS discussions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                book_id INTEGER NOT NULL,
                user_email TEXT NOT NULL,
                title TEXT NOT NULL,
                content TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (book_id) REFERENCES books(id),
                FOREIGN KEY (user_email) REFERENCES users(email)
            )
        ''')
        
        # Discussion replies table
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS discussion_replies (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                discussion_id INTEGER NOT NULL,
                user_email TEXT NOT NULL,
                content TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (discussion_id) REFERENCES discussions(id),
                FOREIGN KEY (user_email) REFERENCES users(email)
            )
        ''')
        
        # User library table
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS user_library (
                user_email TEXT NOT NULL,
                book_id INTEGER NOT NULL,
                last_read TIMESTAMP,
                PRIMARY KEY (user_email, book_id),
                FOREIGN KEY (user_email) REFERENCES users(email),
                FOREIGN KEY (book_id) REFERENCES books(id)
            )
        ''')
        
        # Support queries table
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS support_queries (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_email TEXT NOT NULL,
                subject TEXT NOT NULL,
                content TEXT NOT NULL,
                status TEXT DEFAULT 'Open',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_email) REFERENCES users(email)
            )
        ''')
        
        # Support responses table
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS support_responses (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                query_id INTEGER NOT NULL,
                tech_support_email TEXT NOT NULL,
                content TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (query_id) REFERENCES support_queries(id),
                FOREIGN KEY (tech_support_email) REFERENCES users(email)
            )
        ''')

        # User badges table
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS user_badges (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_email TEXT NOT NULL,
                badge_type TEXT NOT NULL,
                badge_name TEXT NOT NULL,
                date_earned TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_email) REFERENCES users(email)
            )
        ''')
        
        self.conn.commit()

    def hash_password(self, password):
        salt = os.urandom(32)
        key = hashlib.pbkdf2_hmac('sha256', password.encode('utf-8'), salt, 100000)
        return salt + key

    def verify_password(self, stored_password, provided_password):
        if isinstance(stored_password, str):
            stored_password = stored_password.encode('utf-8')
        salt = stored_password[:32]
        stored_key = stored_password[32:]
        new_key = hashlib.pbkdf2_hmac('sha256', provided_password.encode('utf-8'), salt, 100000)
        return stored_key == new_key

    def register_user(self, email, username, password, user_type):
        try:
            hashed_password = self.hash_password(password)
            self.cursor.execute('''
                INSERT INTO users (email, username, password, user_type)
                VALUES (?, ?, ?, ?)
            ''', (email, username, hashed_password, user_type))
            self.conn.commit()
            return True
        except sqlite3.IntegrityError:
            return False

    def login_user(self, email, password):
        self.cursor.execute('SELECT password, user_type FROM users WHERE email = ?', (email,))
        result = self.cursor.fetchone()
        if result and self.verify_password(result[0], password):
            return result[1]  # Return user type
        return None

    def add_sample_books(self):
        """Add sample books to the database if none exist"""
        # Check if books table is empty
        self.cursor.execute("SELECT COUNT(*) FROM books")
        count = self.cursor.fetchone()[0]
        
        if count == 0:
            print("Adding sample books to the database...")
            
            # First, make sure we have at least one author user
            self.cursor.execute("SELECT email FROM users WHERE user_type = 'author' LIMIT 1")
            author = self.cursor.fetchone()
            
            if not author:
                # Create a sample author
                try:
                    hashed_password = self.hash_password("password123")
                    self.cursor.execute('''
                        INSERT INTO users (email, username, password, user_type)
                        VALUES (?, ?, ?, ?)
                    ''', ("author@example.com", "SampleAuthor", hashed_password, "author"))
                    self.conn.commit()
                    author_email = "author@example.com"
                except sqlite3.IntegrityError:
                    # If there's already a user with this email, get another author
                    self.cursor.execute("SELECT email FROM users WHERE user_type = 'author' LIMIT 1")
                    author = self.cursor.fetchone()
                    if author:
                        author_email = author[0]
                    else:
                        print("Could not create or find an author user")
                        return
            else:
                author_email = author[0]
            
            # Sample books data
            sample_books = [
                ("The Great Adventure", "An epic tale of courage and discovery in the uncharted wilderness.", author_email, "https://amazon.com/great-adventure"),
                ("Mystery at Midnight", "A thrilling detective story set in a small coastal town.", author_email, "https://amazon.com/mystery-midnight"),
                ("Science of Tomorrow", "Exploring the latest breakthroughs that will shape our future.", author_email, "https://amazon.com/science-tomorrow"),
                ("The Last Prophecy", "A fantasy novel about the final days of an ancient civilization.", author_email, "https://amazon.com/last-prophecy"),
                ("Cooking with Love", "Recipes and stories that will warm your heart and fill your stomach.", author_email, "https://amazon.com/cooking-love")
            ]
            
            # Insert sample books
            for title, description, author_email, amazon_link in sample_books:
                try:
                    self.cursor.execute('''
                        INSERT INTO books (title, description, author_email, amazon_link, pdf_data)
                        VALUES (?, ?, ?, ?, ?)
                    ''', (title, description, author_email, amazon_link, b'Sample PDF data'))
                except Exception as e:
                    print(f"Error adding sample book {title}: {e}")
            
            self.conn.commit()
            print(f"Added {len(sample_books)} sample books to the database")

class bookverseApp:
    def __init__(self, root):
        self.root = root
        self.root.title("BookVerse Reader")
        self.root.geometry("1024x768")
        
        # Initialize database
        self.db = Database()
        
        # Set up theme - using ttkbootstrap
        self.theme = 'bookverse'  # Custom theme name
        self.dark_mode = False
        
        # Initialize image resources
        self.load_images()
        
        # Colors for light theme
        self.colors = {
            "background": "#FFF5E6",  # Warm peach
            "background_gradient": ["#ffe5d9", "#fcd5ce"],  # Gradient bg colors
            "primary": "#8B4513",     # Brown
            "secondary": "#D2B48C",   # Tan
            "accent": "#A0522D",      # Burnt sienna
            "text": "#4A4A4A",        # Dark gray
            "light_text": "#6B6B6B",  # Lighter gray
            "button_primary": "#8B4513",
            "button_secondary": "#D2B48C",
            "button_highlight": "#A0522D",
            "card_bg": "#FFF9F0",     # Lighter than background
            "card_shadow": "#E5D6C6"  # Slightly darker for shadow
        }
        
        # Colors for dark theme
        self.dark_colors = {
            "background": "#2C2418",  # Deep brown
            "background_gradient": ["#2C2418", "#3D3225"],  # Gradient bg colors
            "primary": "#D2B48C",     # Tan
            "secondary": "#8B4513",   # Brown
            "accent": "#CD853F",      # Peru
            "text": "#E0E0E0",        # Light gray
            "light_text": "#BCBCBC",  # Very light gray
            "button_primary": "#D2B48C",
            "button_secondary": "#A0522D",
            "button_highlight": "#CD853F",
            "card_bg": "#3D3225",     # Lighter than background
            "card_shadow": "#1F1A14"  # Darker for shadow
        }
        
        # Configure styles
        self.configure_styles()
        
        # Create authentication frame
        self.auth_frame = ttk.Frame(self.root, style="Auth.TFrame")
        self.auth_frame.pack(expand=True, fill="both")
        
        # Show authentication screen
        self.show_auth_screen()
        
    def load_images(self):
        """Load and initialize all images and icons used in the app"""
        self.images = {}
        
        # Create coffee cup image for login screen
        coffee_img = self.create_coffee_cup_image(180, 180)
        self.images['coffee'] = ImageTk.PhotoImage(coffee_img)
        
        # Create book icon
        book_img = self.create_book_icon(100, 100)
        self.images['book'] = ImageTk.PhotoImage(book_img)
        
        # Create cat icon
        cat_img = self.create_cat_icon(150, 150)
        self.images['cat'] = ImageTk.PhotoImage(cat_img)
        
        # Create bookshelf background
        bookshelf_img = self.create_bookshelf_image(1024, 768)
        self.images['bookshelf'] = ImageTk.PhotoImage(bookshelf_img)
        
        # Create user avatar placeholder
        avatar_img = self.create_avatar_placeholder(100, 100, "UU")
        self.images['avatar'] = ImageTk.PhotoImage(avatar_img)
        
        # Create home icon
        home_img = self.create_home_icon(24, 24)
        self.images['home'] = ImageTk.PhotoImage(home_img)
        
        # Create bookmark icon
        bookmark_img = self.create_bookmark_icon(24, 24)
        self.images['bookmark'] = ImageTk.PhotoImage(bookmark_img)
        
        # Create badge icons
        reader_badge_img = self.create_badge_icon(24, 24, "📚")
        self.images['reader_badge'] = ImageTk.PhotoImage(reader_badge_img)
        
        reviewer_badge_img = self.create_badge_icon(24, 24, "⭐")
        self.images['reviewer_badge'] = ImageTk.PhotoImage(reviewer_badge_img)
        
        author_badge_img = self.create_badge_icon(24, 24, "✍️")
        self.images['author_badge'] = ImageTk.PhotoImage(author_badge_img)
    
    def create_coffee_cup_image(self, width, height):
        """Create a coffee cup image"""
        img = Image.new('RGBA', (width, height), (255, 0, 0, 0))
        draw = ImageDraw.Draw(img)
        
        # Cup base
        cup_color = (186, 124, 92)
        draw.rounded_rectangle([width//4, height//4, 3*width//4, 3*height//4], 
                             fill=cup_color, radius=15)
        
        # Cup handle
        draw.arc([3*width//4, height//3, 7*width//8, 2*height//3], 0, 180, fill=cup_color, width=8)
        
        # Coffee liquid
        coffee_color = (101, 67, 33)
        draw.rounded_rectangle([width//4 + 10, height//4 + 10, 3*width//4 - 10, height//4 + 40], 
                             fill=coffee_color, radius=5)
        
        # Steam
        steam_color = (200, 200, 200, 150)
        for i in range(3):
            x_offset = width//2 + (i-1) * 15
            for j in range(3):
                draw.arc([x_offset - 10, height//5 - j*10 - 20, 
                        x_offset + 10, height//5 - j*10], 
                       180, 0, fill=steam_color, width=3)
        
        return img
    
    def create_book_icon(self, width, height):
        """Create a book icon"""
        img = Image.new('RGBA', (width, height), (255, 0, 0, 0))
        draw = ImageDraw.Draw(img)
        
        # Book cover
        book_color = (139, 69, 19)  # Brown
        draw.rounded_rectangle([width//8, height//8, 7*width//8, 7*height//8], 
                             fill=book_color, radius=5)
        
        # Book pages
        page_color = (255, 250, 240)  # Floral white
        draw.rounded_rectangle([width//8 + 5, height//8 + 5, 7*width//8 - 15, 7*height//8 - 5], 
                             fill=page_color, radius=3)
        
        # Book binding
        binding_color = (101, 67, 33)  # Dark brown
        draw.rectangle([width//8, height//8, width//8 + 10, 7*height//8], 
                     fill=binding_color)
        
        # Book title lines
        line_color = (200, 200, 200)
        for i in range(3):
            y_pos = height//3 + i * height//8
            draw.line([width//4, y_pos, 3*width//4, y_pos], fill=line_color, width=2)
        
        return img
    
    def create_cat_icon(self, width, height):
        """Create a cute cat icon"""
        img = Image.new('RGBA', (width, height), (255, 0, 0, 0))
        draw = ImageDraw.Draw(img)
        
        # Cat body
        cat_color = (255, 165, 79)  # Orange
        draw.ellipse([width//4, height//3, 3*width//4, 7*height//8], fill=cat_color)
        
        # Cat head
        draw.ellipse([width//4, height//8, 3*width//4, 2*height//3], fill=cat_color)
        
        # Cat ears
        draw.polygon([width//4, height//3, width//3, height//8, 5*width//12, height//3], fill=cat_color)
        draw.polygon([3*width//4, height//3, 2*width//3, height//8, 7*width//12, height//3], fill=cat_color)
        
        # Cat inner ears
        inner_ear_color = (255, 192, 137)
        draw.polygon([width//4 + 5, height//3 - 5, width//3 + 2, height//8 + 10, 5*width//12 - 5, height//3 - 5], fill=inner_ear_color)
        draw.polygon([3*width//4 - 5, height//3 - 5, 2*width//3 - 2, height//8 + 10, 7*width//12 + 5, height//3 - 5], fill=inner_ear_color)
        
        # Cat eyes (closed for sleeping)
        eye_color = (50, 30, 10)
        draw.line([width//3, height//2, 5*width//12, height//2 - 5], fill=eye_color, width=2)
        draw.line([2*width//3, height//2, 7*width//12, height//2 - 5], fill=eye_color, width=2)
        
        # Cat nose
        nose_color = (255, 120, 120)
        draw.ellipse([width//2 - 5, height//2 + 5, width//2 + 5, height//2 + 15], fill=nose_color)
        
        # Cat stripes
        stripe_color = (220, 140, 60)
        for i in range(3):
            y_pos = 2*height//3 + i * height//10
            draw.arc([width//4 + 10, y_pos, 3*width//4 - 10, y_pos + 20], 0, 180, fill=stripe_color, width=3)
        
        return img
    
    def create_bookshelf_image(self, width, height):
        """Create a bookshelf background image"""
        img = Image.new('RGBA', (width, height), (255, 0, 0, 0))
        draw = ImageDraw.Draw(img)
        
        # Background gradient
        for y in range(height):
            r = int(255 - (y / height) * 30)
            g = int(245 - (y / height) * 30)
            b = int(230 - (y / height) * 30)
            draw.line([(0, y), (width, y)], fill=(r, g, b))
        
        # Shelf wood
        shelf_color = (139, 69, 19)  # Brown
        
        # Draw shelves
        for i in range(3):
            y_pos = height//4 + i * height//4
            draw.rectangle([0, y_pos, width, y_pos + 15], fill=shelf_color)
        
        # Draw vertical supports
        draw.rectangle([0, 0, 15, height], fill=shelf_color)
        draw.rectangle([width - 15, 0, width, height], fill=shelf_color)
        
        # Add some subtle texture to the wood
        for i in range(20):
            x = random.randint(0, width)
            y = random.randint(0, height)
            if (y // (height//4)) * (height//4) <= y <= (y // (height//4)) * (height//4) + 15:
                draw.line([(x, y), (x + random.randint(5, 20), y)], 
                        fill=(139, 69, 19, 150), width=1)
        
        # Add some books on shelves
        book_colors = [
            (210, 105, 30),  # Chocolate
            (165, 42, 42),   # Brown
            (128, 0, 0),     # Maroon
            (139, 0, 0),     # Dark Red
            (178, 34, 34),   # Firebrick
            (220, 20, 60),   # Crimson
            (255, 0, 0),     # Red
            (255, 99, 71),   # Tomato
            (255, 127, 80),  # Coral
            (205, 92, 92),   # Indian Red
            (240, 128, 128), # Light Coral
            (233, 150, 122), # Dark Salmon
            (250, 128, 114), # Salmon
            (255, 160, 122), # Light Salmon
            (255, 69, 0),    # Orange Red
            (255, 140, 0),   # Dark Orange
            (255, 165, 0),   # Orange
            (255, 215, 0),   # Gold
            (184, 134, 11),  # Dark Goldenrod
            (218, 165, 32),  # Goldenrod
            (238, 232, 170), # Pale Goldenrod
            (189, 183, 107), # Dark Khaki
            (240, 230, 140), # Khaki
            (128, 128, 0),   # Olive
            (154, 205, 50),  # Yellow Green
            (85, 107, 47),   # Dark Olive Green
            (107, 142, 35),  # Olive Drab
            (124, 252, 0),   # Lawn Green
            (127, 255, 0),   # Chartreuse
            (173, 255, 47),  # Green Yellow
            (0, 100, 0),     # Dark Green
            (0, 128, 0),     # Green
            (34, 139, 34),   # Forest Green
            (0, 255, 0),     # Lime
            (50, 205, 50),   # Lime Green
            (144, 238, 144), # Light Green
            (152, 251, 152), # Pale Green
            (143, 188, 143), # Dark Sea Green
            (0, 250, 154),   # Medium Spring Green
            (0, 255, 127),   # Spring Green
            (46, 139, 87),   # Sea Green
            (102, 205, 170), # Medium Aquamarine
            (60, 179, 113),  # Medium Sea Green
            (32, 178, 170),  # Light Sea Green
            (47, 79, 79),    # Dark Slate Gray
            (0, 128, 128),   # Teal
            (0, 139, 139),   # Dark Cyan
            (0, 255, 255),   # Cyan
            (224, 255, 255), # Light Cyan
            (0, 206, 209),   # Dark Turquoise
            (64, 224, 208),  # Turquoise
            (72, 209, 204),  # Medium Turquoise
            (175, 238, 238), # Pale Turquoise
            (127, 255, 212), # Aquamarine
            (176, 224, 230), # Powder Blue
            (95, 158, 160),  # Cadet Blue
            (70, 130, 180),  # Steel Blue
            (100, 149, 237), # Cornflower Blue
            (0, 191, 255),   # Deep Sky Blue
            (30, 144, 255),  # Dodger Blue
            (173, 216, 230), # Light Blue
            (135, 206, 235), # Sky Blue
            (135, 206, 250), # Light Sky Blue
            (25, 25, 112),   # Midnight Blue
            (0, 0, 128),     # Navy
            (0, 0, 139),     # Dark Blue
            (0, 0, 205),     # Medium Blue
            (0, 0, 255),     # Blue
            (65, 105, 225),  # Royal Blue
            (138, 43, 226),  # Blue Violet
            (75, 0, 130),    # Indigo
            (72, 61, 139),   # Dark Slate Blue
            (106, 90, 205),  # Slate Blue
            (123, 104, 238), # Medium Slate Blue
            (147, 112, 219), # Medium Purple
            (139, 0, 139),   # Dark Magenta
            (148, 0, 211),   # Dark Violet
            (153, 50, 204),  # Dark Orchid
            (186, 85, 211),  # Medium Orchid
            (128, 0, 128),   # Purple
            (216, 191, 216), # Thistle
            (221, 160, 221), # Plum
            (238, 130, 238), # Violet
            (255, 0, 255),   # Magenta
            (218, 112, 214), # Orchid
            (199, 21, 133),  # Medium Violet Red
            (219, 112, 147), # Pale Violet Red
            (255, 20, 147),  # Deep Pink
            (255, 105, 180), # Hot Pink
            (255, 182, 193), # Light Pink
            (255, 192, 203), # Pink
            (250, 235, 215), # Antique White
            (245, 245, 220), # Beige
            (255, 228, 196), # Bisque
            (255, 235, 205), # Blanched Almond
            (255, 248, 220), # Cornsilk
            (255, 250, 205), # Lemon Chiffon
            (255, 245, 238), # Seashell
            (245, 255, 250), # Mint Cream
            (240, 255, 240), # Honeydew
            (240, 248, 255), # Alice Blue
            (248, 248, 255), # Ghost White
            (240, 255, 255), # Azure
            (255, 255, 240), # Ivory
            (255, 250, 240), # Floral White
            (253, 245, 230), # Old Lace
            (255, 239, 213), # Papaya Whip
            (255, 228, 181), # Moccasin
            (255, 222, 173), # Navajo White
            (255, 218, 185), # Peach Puff
            (255, 228, 225), # Misty Rose
            (255, 240, 245), # Lavender Blush
            (255, 255, 255), # White
            (230, 230, 250), # Lavender
            (245, 245, 245), # White Smoke
            (0, 0, 0)        # Black
        ]
        
        for shelf_num in range(3):
            y_pos = height//4 + shelf_num * height//4 - height//8
            x_pos = 20
            while x_pos < width - 40:
                book_width = random.randint(20, 40)
                book_height = random.randint(100, 180)
                book_color = random.choice(book_colors)
                
                if x_pos + book_width < width - 20:
                    # Draw book
                    draw.rectangle([x_pos, y_pos - book_height, x_pos + book_width, y_pos], 
                                 fill=book_color)
                    
                    # Draw book spine details
                    spine_color = (min(book_color[0] + 30, 255), 
                                 min(book_color[1] + 30, 255), 
                                 min(book_color[2] + 30, 255))
                    
                    # Draw spine line
                    draw.line([
                        (x_pos + book_width//2, y_pos - book_height + 10),
                        (x_pos + book_width//2, y_pos - 10)
                    ], fill=spine_color, width=1)
                    
                    x_pos += book_width + 5
                else:
                    break
        
        return img
    
    def create_avatar_placeholder(self, width, height, initials=""):
        """Create a placeholder avatar with initials"""
        img = Image.new('RGBA', (width, height), (255, 0, 0, 0))
        draw = ImageDraw.Draw(img)
        
        # Draw circle
        circle_color = random.choice([
            (142, 68, 173),  # Purple
            (41, 128, 185),  # Blue
            (39, 174, 96),   # Green
            (211, 84, 0),    # Orange
            (231, 76, 60),   # Red
            (52, 73, 94)     # Dark Blue
        ])
        draw.ellipse([(0, 0), (width, height)], fill=circle_color)
        
        # Draw text
        # Note: In a real app you'd use a proper font with ImageFont.truetype()
        if initials:
            text_position = (width//2, height//2)
            draw.text(text_position, initials, fill="white", anchor="mm")
        
        return img
    
    def create_home_icon(self, width, height):
        """Create a home icon"""
        img = Image.new('RGBA', (width, height), (255, 0, 0, 0))
        draw = ImageDraw.Draw(img)
        
        # House outline
        draw.polygon([
            (width//2, 0),           # top point
            (0, height//2),          # left point
            (width//5, height//2),   # left door start
            (width//5, height),      # bottom left
            (4*width//5, height),    # bottom right
            (4*width//5, height//2), # right door start
            (width, height//2)       # right point
        ], fill=(139, 69, 19))
        
        # Door
        draw.rectangle([
            (2*width//5, 3*height//5),
            (3*width//5, height)
        ], fill=(101, 67, 33))
        
        # Doorknob
        draw.ellipse([
            (2*width//5 + 2, 3*height//4),
            (2*width//5 + 6, 3*height//4 + 4)
        ], fill=(255, 215, 0))
        
        return img
    
    def create_bookmark_icon(self, width, height):
        """Create a bookmark icon"""
        img = Image.new('RGBA', (width, height), (255, 0, 0, 0))
        draw = ImageDraw.Draw(img)
        
        # Bookmark shape
        draw.polygon([
            (width//4, 0),         # top left
            (3*width//4, 0),       # top right
            (3*width//4, height),  # bottom right
            (width//2, 3*height//4), # bottom middle
            (width//4, height)     # bottom left
        ], fill=(139, 0, 0))
        
        return img
    
    def create_badge_icon(self, width, height, symbol=""):
        """Create a badge icon with a symbol"""
        img = Image.new('RGBA', (width, height), (255, 0, 0, 0))
        draw = ImageDraw.Draw(img)
        
        # Badge circle
        badge_color = (255, 215, 0)  # Gold
        draw.ellipse([(0, 0), (width, height)], fill=badge_color)
        
        # Border
        border_color = (218, 165, 32)  # Darker gold
        draw.ellipse([(0, 0), (width, height)], outline=border_color, width=2)
        
        # Symbol
        if symbol:
            text_position = (width//2, height//2)
            draw.text(text_position, symbol, fill=(139, 69, 19), anchor="mm")
        
        return img
    
    def generate_avatar_for_user(self, username, email):
        """Generate an avatar based on user's username and email"""
        if not username:
            username = "User"
            
        # Create initials from username
        initials = "".join([name[0].upper() for name in username.split() if name])
        if not initials:
            initials = username[0].upper()
        
        # Hash the email to get a consistent color
        hash_value = int(hashlib.md5(email.encode()).hexdigest(), 16)
        r = (hash_value & 0xFF0000) >> 16
        g = (hash_value & 0x00FF00) >> 8
        b = hash_value & 0x0000FF
        
        # Create background with consistent color
        background_color = (r, g, b)
        
        # Create the avatar
        img = Image.new('RGBA', (100, 100), (255, 0, 0, 0))
        draw = ImageDraw.Draw(img)
        
        # Draw circle with the consistent color
        draw.ellipse([(0, 0), (100, 100)], fill=background_color)
        
        # Draw text
        # Note: In a real app you'd use a proper font
        text_position = (50, 50)
        draw.text(text_position, initials, fill="white", anchor="mm")
        
        return img

    def configure_styles(self):
        """Configure ttk styles for the application"""
        # Create ttkbootstrap style
        self.style = tb.Style(theme="cosmo")
        
        # Customize the theme
        self.style.configure("TLabel", background=self.colors["background"], 
                       foreground=self.colors["text"],
                          font=("Garamond", 11))
        
        self.style.configure("Title.TLabel", 
                          font=("Garamond", 20, "bold"),
                          foreground=self.colors["primary"])
        
        self.style.configure("Subtitle.TLabel", 
                          font=("Quicksand", 14),
                          foreground=self.colors["secondary"])
        
        self.style.configure("TFrame", background=self.colors["background"])
        
        self.style.configure("Card.TFrame", 
                          background=self.colors["card_bg"],
                          relief="raised",
                          borderwidth=0)
        
        self.style.configure("Auth.TFrame", background=self.colors["background"])
        
        self.style.configure("TButton", 
                          font=("Quicksand", 11),
                       background=self.colors["button_primary"],
                          foreground="white")
        
        self.style.map("TButton",
                    background=[('active', self.colors["button_highlight"])],
                    relief=[('pressed', 'sunken'), ('!pressed', 'raised')])
        
        self.style.configure("Primary.TButton", 
                          font=("Quicksand", 11, "bold"),
                          background=self.colors["button_primary"],
                          foreground="white")
        
        self.style.configure("Secondary.TButton", 
                          font=("Quicksand", 11),
                          background=self.colors["button_secondary"],
                          foreground="white")
        
        self.style.configure("TEntry", 
                          font=("Quicksand", 11),
                          fieldbackground="white")
        
        self.style.configure("TCombobox", 
                          font=("Quicksand", 11),
                          fieldbackground="white")
        
        # Configure the root window
        self.root.configure(bg=self.colors["background"])
        
        # Create a custom scrollbar style
        self.style.configure("Custom.Vertical.TScrollbar", 
                          background=self.colors["button_secondary"],
                          arrowcolor=self.colors["primary"],
                          troughcolor=self.colors["background"],
                          relief="flat",
                          borderwidth=0)
    
    def toggle_theme(self):
        """Toggle between light and dark theme"""
        self.dark_mode = not self.dark_mode
        
        # Update colors based on theme
        if self.dark_mode:
            self.colors = self.dark_colors
        else:
            self.colors = {
                "background": "#FFF5E6",  # Warm peach
                "background_gradient": ["#ffe5d9", "#fcd5ce"],  # Gradient bg colors
                "primary": "#8B4513",     # Brown
                "secondary": "#D2B48C",   # Tan
                "accent": "#A0522D",      # Burnt sienna
                "text": "#4A4A4A",        # Dark gray
                "light_text": "#6B6B6B",  # Lighter gray
                "button_primary": "#8B4513",
                "button_secondary": "#D2B48C",
                "button_highlight": "#A0522D",
                "card_bg": "#FFF9F0",     # Lighter than background
                "card_shadow": "#E5D6C6"  # Slightly darker for shadow
            }
        
        # Update styles
        self.configure_styles()
        
        # Refresh the current screen to apply new styles
        if hasattr(self, 'auth_frame') and self.auth_frame.winfo_exists():
            self.show_auth_screen()
        elif hasattr(self, 'current_user'):
            # Refresh main interface
            self.main_frame.destroy()
            self.show_main_interface()

    def show_auth_screen(self):
        """Display the authentication screen with cozy design"""
        # Clear the auth frame
        for widget in self.auth_frame.winfo_children():
            widget.destroy()
        
        # Create background canvas with gradient
        canvas = tk.Canvas(self.auth_frame, bg=self.colors["background"],
                         highlightthickness=0, width=1024, height=768)
        canvas.pack(fill="both", expand=True)
        
        # Draw gradient background
        self.draw_gradient_background(canvas, 1024, 768, 
                                   self.colors["background_gradient"][0], 
                                   self.colors["background_gradient"][1])
        
        # Add bookshelf image
        canvas.create_image(512, 384, image=self.images["bookshelf"])
        
        # Create content frame
        content_frame = ttk.Frame(canvas, style="Auth.TFrame")
        content_frame.place(relx=0.5, rely=0.5, anchor="center")
        
        # Add welcome message with logo and images
        logo_frame = ttk.Frame(content_frame, style="Auth.TFrame")
        logo_frame.pack(pady=20)
        
        # Add coffee cup and book images next to logo
        book_label = ttk.Label(logo_frame, image=self.images["book"], background=self.colors["background"])
        book_label.pack(side=tk.LEFT, padx=10)
        
        welcome_label = ttk.Label(logo_frame,
                                text="BookVerse Reader",
                                font=("Garamond", 32, "bold"),
                                foreground=self.colors["primary"],
                                background=self.colors["background"])
        welcome_label.pack(side=tk.LEFT, padx=10)
        
        coffee_label = ttk.Label(logo_frame, image=self.images["coffee"], background=self.colors["background"])
        coffee_label.pack(side=tk.LEFT, padx=10)
        
        # Add quote
        quote_frame = ttk.Frame(content_frame, style="Auth.TFrame")
        quote_frame.pack(pady=5)
        
        quote_label = ttk.Label(quote_frame,
                              text='"A reader lives a thousand lives before he dies."\n- George R.R. Martin',
                              font=("Garamond", 16, "italic"),
                              foreground=self.colors["text"],
                              background=self.colors["background"])
        quote_label.pack()
        
        # Add login/register buttons in a card
        card_frame = ttk.Frame(content_frame, style="Card.TFrame")
        card_frame.pack(pady=20, padx=20, ipadx=30, ipady=20)
        
        # Apply shadow effect to card
        self.apply_shadow_effect(card_frame)
        
        # Title in card
        ttk.Label(card_frame,
                text="Welcome to your cozy reading corner",
                font=("Garamond", 18, "bold"),
                foreground=self.colors["primary"],
                background=self.colors["card_bg"]).pack(pady=10)
        
        # Add the cat image
        cat_label = ttk.Label(card_frame, image=self.images["cat"], background=self.colors["card_bg"])
        cat_label.pack(pady=5)
        
        # Buttons in card
        button_frame = ttk.Frame(card_frame, style="Card.TFrame")
        button_frame.pack(pady=15)
        
        login_btn = tk.Button(button_frame,
                            text="Snuggle In",
                            command=self.show_login_form,
                            bg=self.colors["button_primary"],
                            fg="white",
                            font=("Quicksand", 12, "bold"),
                            relief=tk.FLAT,
                            borderwidth=0,
                            padx=20,
                            pady=8,
                            cursor="hand2")
        login_btn.pack(side=tk.LEFT, padx=10)
        self.apply_hover_effect(login_btn)
        
        register_btn = tk.Button(button_frame,
                               text="Join the Bookshelf",
                               command=self.show_register_form,
                               bg=self.colors["button_secondary"],
                               fg="white",
                               font=("Quicksand", 12),
                               relief=tk.FLAT,
                               borderwidth=0,
                               padx=20,
                               pady=8,
                               cursor="hand2")
        register_btn.pack(side=tk.LEFT, padx=10)
        self.apply_hover_effect(register_btn)
        
        # Add theme toggle button
        theme_btn = tk.Button(content_frame,
                            text="☀ / ☽",
                            command=self.toggle_theme,
                            bg=self.colors["button_secondary"],
                            fg="white",
                            font=("Quicksand", 10),
                            relief=tk.FLAT,
                            borderwidth=0,
                            padx=10,
                            pady=5,
                            cursor="hand2")
        theme_btn.pack(pady=10)
    
    def draw_gradient_background(self, canvas, width, height, color1, color2):
        """Draw a gradient background on a canvas"""
        for i in range(height):
            # Calculate color for this line as a blend between color1 and color2
            r1, g1, b1 = self.hex_to_rgb(color1)
            r2, g2, b2 = self.hex_to_rgb(color2)
            
            ratio = i / height
            r = int(r1 * (1 - ratio) + r2 * ratio)
            g = int(g1 * (1 - ratio) + g2 * ratio)
            b = int(b1 * (1 - ratio) + b2 * ratio)
            
            color = f'#{r:02x}{g:02x}{b:02x}'
            canvas.create_line(0, i, width, i, fill=color)
    
    def hex_to_rgb(self, hex_color):
        """Convert hex color to RGB tuple"""
        hex_color = hex_color.lstrip('#')
        return tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))
    
    def apply_shadow_effect(self, widget):
        """Apply a subtle shadow effect to a widget"""
        # This is a simplified shadow effect
        # In a real app, you might use a more sophisticated approach with a canvas
        shadow_frame = ttk.Frame(widget.master, style="TFrame")
        shadow_frame.place(in_=widget, x=5, y=5, relwidth=1, relheight=1)
        widget.lift()
    
    def apply_hover_effect(self, button):
        """Apply hover effect to a button"""
        orig_bg = button.cget("background")
        hover_bg = self.colors["button_highlight"]
        
        def on_enter(e):
            button.config(background=hover_bg)
            
        def on_leave(e):
            button.config(background=orig_bg)
            
        button.bind("<Enter>", on_enter)
        button.bind("<Leave>", on_leave)
        
    def create_rounded_button(self, parent, text, command, primary=True):
        """Create a rounded button with hover effects"""
        if primary:
            bg_color = self.colors["button_primary"]
            hover_color = self.colors["button_highlight"]
        else:
            bg_color = self.colors["button_secondary"]
            hover_color = self.colors["accent"]
            
        button = tk.Button(parent,
                         text=text,
                         command=command,
                         bg=bg_color,
                         fg="white",
                         font=("Quicksand", 12),
                         relief=tk.FLAT,
                         borderwidth=0,
                         padx=20,
                         pady=8,
                         cursor="hand2")
        
        # Add hover effect
        def on_enter(e):
            button.config(background=hover_color)
            
        def on_leave(e):
            button.config(background=bg_color)
            
        button.bind("<Enter>", on_enter)
        button.bind("<Leave>", on_leave)
        
        return button

    def show_login_form(self):
        """Display the login form with cozy design"""
        # Clear the auth frame
        for widget in self.auth_frame.winfo_children():
            widget.destroy()
        
        # Create background canvas with gradient
        canvas = tk.Canvas(self.auth_frame, bg=self.colors["background"],
                         highlightthickness=0, width=1024, height=768)
        canvas.pack(fill="both", expand=True)
        
        # Draw gradient background
        self.draw_gradient_background(canvas, 1024, 768, 
                                   self.colors["background_gradient"][0], 
                                   self.colors["background_gradient"][1])
        
        # Add bookshelf image
        canvas.create_image(512, 384, image=self.images["bookshelf"])
        
        # Create login form within a card
        card_frame = ttk.Frame(canvas, style="Card.TFrame")
        card_width = 400
        card_height = 450
        card_frame.place(x=(1024-card_width)//2, y=(768-card_height)//2,
                       width=card_width, height=card_height)
        
        # Apply shadow effect
        shadow_frame = ttk.Frame(canvas, style="TFrame")
        shadow_frame.place(x=(1024-card_width)//2 + 5, y=(768-card_height)//2 + 5,
                         width=card_width, height=card_height)
        card_frame.lift()
        
        # Title with book icon
        header_frame = ttk.Frame(card_frame, style="Card.TFrame")
        header_frame.pack(pady=20)
        
        book_label = ttk.Label(header_frame, image=self.images["book"], background=self.colors["card_bg"])
        book_label.pack(side=tk.LEFT, padx=5)
        
        title_label = ttk.Label(header_frame,
                              text="Welcome Back",
                              font=("Garamond", 24, "bold"),
                              foreground=self.colors["primary"],
                              background=self.colors["card_bg"])
        title_label.pack(side=tk.LEFT, padx=5)
        
        # Email field with improved styling
        email_frame = ttk.Frame(card_frame, style="Card.TFrame")
        email_frame.pack(pady=10, padx=30, fill="x")
        
        email_label = ttk.Label(email_frame, 
                              text="Email:",
                              font=("Quicksand", 12),
                              foreground=self.colors["text"],
                              background=self.colors["card_bg"])
        email_label.pack(anchor="w")
        
        self.login_email = ttk.Entry(email_frame, width=30, font=("Quicksand", 12))
        self.login_email.pack(fill="x", pady=5)
        
        # Password field with improved styling
        password_frame = ttk.Frame(card_frame, style="Card.TFrame")
        password_frame.pack(pady=10, padx=30, fill="x")
        
        password_label = ttk.Label(password_frame, 
                                 text="Password:",
                                 font=("Quicksand", 12),
                                 foreground=self.colors["text"],
                                 background=self.colors["card_bg"])
        password_label.pack(anchor="w")
        
        self.login_password = ttk.Entry(password_frame, width=30, font=("Quicksand", 12), show="*")
        self.login_password.pack(fill="x", pady=5)
        
        # Login button
        button_frame = ttk.Frame(card_frame, style="Card.TFrame")
        button_frame.pack(pady=20)
        
        login_btn = self.create_rounded_button(button_frame, "Snuggle In", self.login, primary=True)
        login_btn.pack()
        
        # Back button
        back_btn = self.create_rounded_button(card_frame, "← Back", self.show_auth_screen, primary=False)
        back_btn.pack(pady=10)
        
        # Add the cat at the bottom
        cat_label = ttk.Label(card_frame, image=self.images["cat"], background=self.colors["card_bg"])
        cat_label.pack(side="bottom", pady=10)

    def show_register_form(self):
        """Display the registration form with cozy design"""
        # Clear the auth frame
        for widget in self.auth_frame.winfo_children():
            widget.destroy()
        
        # Create background canvas with gradient
        canvas = tk.Canvas(self.auth_frame, bg=self.colors["background"],
                         highlightthickness=0, width=1024, height=768)
        canvas.pack(fill="both", expand=True)
        
        # Draw gradient background
        self.draw_gradient_background(canvas, 1024, 768, 
                                   self.colors["background_gradient"][0], 
                                   self.colors["background_gradient"][1])
        
        # Add bookshelf image
        canvas.create_image(512, 384, image=self.images["bookshelf"])
        
        # Create main scroll frame
        main_frame = ttk.Frame(canvas)
        main_frame.place(relx=0.5, rely=0.5, anchor="center")
        
        # Create a scrollable frame for the registration form
        container = ttk.Frame(main_frame)
        container.pack(fill="both", expand=True)
        
        # Create canvas with scrollbar
        canvas = tk.Canvas(container, bg=self.colors["card_bg"],
                         highlightthickness=0, width=500, height=600)
        scrollbar = ttk.Scrollbar(container, orient="vertical", command=canvas.yview)
        scrollbar.pack(side="right", fill="y")
        canvas.pack(side="left", fill="both", expand=True)
        canvas.configure(yscrollcommand=scrollbar.set)
        
        # Create registration form card within the canvas
        card_frame = ttk.Frame(canvas, style="Card.TFrame")
        card_frame.bind("<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
        
        canvas.create_window((0, 0), window=card_frame, anchor="nw", width=480)
        
        # Apply shadow effect
        self.apply_shadow_effect(container)
        
        # Title with book icon
        header_frame = ttk.Frame(card_frame, style="Card.TFrame")
        header_frame.pack(pady=20)
        
        book_label = ttk.Label(header_frame, image=self.images["book"], background=self.colors["card_bg"])
        book_label.pack(side=tk.LEFT, padx=5)
        
        title_label = ttk.Label(header_frame,
                              text="Join the Bookshelf",
                              font=("Garamond", 24, "bold"),
                              foreground=self.colors["primary"],
                              background=self.colors["card_bg"])
        title_label.pack(side=tk.LEFT, padx=5)
        
        # Registration form fields
        # Email
        self.create_form_field(card_frame, "Email:", "register_email")
        
        # Username
        self.create_form_field(card_frame, "Username:", "register_username")
        
        # Password
        password_frame = ttk.Frame(card_frame, style="Card.TFrame")
        password_frame.pack(pady=10, padx=30, fill="x")
        
        password_label = ttk.Label(password_frame, 
                                 text="Password:",
                                 font=("Quicksand", 12),
                                 foreground=self.colors["text"],
                                 background=self.colors["card_bg"])
        password_label.pack(anchor="w")
        
        self.register_password = ttk.Entry(password_frame, width=30, font=("Quicksand", 12), show="*")
        self.register_password.pack(fill="x", pady=5)
        
        # Full Name
        self.create_form_field(card_frame, "Full Name:", "register_full_name")
        
        # Date of Birth
        self.create_form_field(card_frame, "Date of Birth (YYYY-MM-DD):", "register_dob")
        
        # Gender
        gender_frame = ttk.Frame(card_frame, style="Card.TFrame")
        gender_frame.pack(pady=10, padx=30, fill="x")
        
        gender_label = ttk.Label(gender_frame, 
                               text="Gender:",
                               font=("Quicksand", 12),
                               foreground=self.colors["text"],
                               background=self.colors["card_bg"])
        gender_label.pack(anchor="w")
        
        self.register_gender = ttk.Combobox(gender_frame, 
                                          values=["Male", "Female", "Other"],
                                          font=("Quicksand", 12),
                                          width=27)
        self.register_gender.pack(fill="x", pady=5)
        
        # Book Genre Preference
        genre_frame = ttk.Frame(card_frame, style="Card.TFrame")
        genre_frame.pack(pady=10, padx=30, fill="x")
        
        genre_label = ttk.Label(genre_frame, 
                              text="Favorite Genre:",
                              font=("Quicksand", 12),
                              foreground=self.colors["text"],
                              background=self.colors["card_bg"])
        genre_label.pack(anchor="w")
        
        self.register_genre = ttk.Combobox(genre_frame, 
                                         values=["Fiction", "Non-Fiction", "Mystery", "Science Fiction", 
                                                "Fantasy", "Romance", "Biography", "History", "Self-Help"],
                                         font=("Quicksand", 12),
                                         width=27)
        self.register_genre.pack(fill="x", pady=5)
        
        # User type
        type_frame = ttk.Frame(card_frame, style="Card.TFrame")
        type_frame.pack(pady=10, padx=30, fill="x")
        
        type_label = ttk.Label(type_frame, 
                             text="I am a:",
                             font=("Quicksand", 12),
                             foreground=self.colors["text"],
                             background=self.colors["card_bg"])
        type_label.pack(anchor="w")
        
        self.user_type = tk.StringVar(value="reader")
        
        radio_frame = ttk.Frame(type_frame, style="Card.TFrame")
        radio_frame.pack(fill="x", pady=5)
        
        reader_radio = ttk.Radiobutton(radio_frame, 
                                     text="Reader", 
                                     variable=self.user_type, 
                                     value="reader",
                                     style="TRadiobutton")
        reader_radio.pack(side=tk.LEFT, padx=10)
        
        author_radio = ttk.Radiobutton(radio_frame, 
                                     text="Author", 
                                     variable=self.user_type, 
                                     value="author",
                                     style="TRadiobutton")
        author_radio.pack(side=tk.LEFT, padx=10)
        
        # Register button
        button_frame = ttk.Frame(card_frame, style="Card.TFrame")
        button_frame.pack(pady=20)
        
        register_btn = self.create_rounded_button(button_frame, "Join the Bookshelf", self.register, primary=True)
        register_btn.pack()
        
        # Back button
        back_btn = self.create_rounded_button(card_frame, "← Back", self.show_auth_screen, primary=False)
        back_btn.pack(pady=10)
    
    def create_form_field(self, parent, label_text, attribute_name):
        """Create a form field with label and entry"""
        frame = ttk.Frame(parent, style="Card.TFrame")
        frame.pack(pady=10, padx=30, fill="x")
        
        label = ttk.Label(frame, 
                        text=label_text,
                        font=("Quicksand", 12),
                        foreground=self.colors["text"],
                        background=self.colors["card_bg"])
        label.pack(anchor="w")
        
        entry = ttk.Entry(frame, width=30, font=("Quicksand", 12))
        entry.pack(fill="x", pady=5)
        
        # Set the attribute on self
        setattr(self, attribute_name, entry)
        
        return frame

    def login(self):
        """Handle user login"""
        email = self.login_email.get()
        password = self.login_password.get()
        
        if not email or not password:
            self.show_toast("Please fill in all fields", "error")
            return
        
        # Hardcoded tech support credentials
        if email == "techsupport@bookverse.com" and password == "admin123":
            self.current_user = email
            self.user_type = "tech_support"
            # Create a default username for tech support
            self.tech_support_username = "Tech Support"
            self.auth_frame.destroy()
            self.show_main_interface()
            return
        
        user_type = self.db.login_user(email, password)
        if user_type:
            self.current_user = email
            self.user_type = user_type
            self.auth_frame.destroy()
            self.show_main_interface()
            self.show_toast(f"Welcome back!", "success")
        else:
            self.show_toast("Invalid email or password", "error")
            
    def register(self):
        """Handle user registration"""
        email = self.register_email.get()
        username = self.register_username.get()
        password = self.register_password.get()
        full_name = self.register_full_name.get()
        user_type = self.user_type.get()
        date_of_birth = self.register_dob.get()
        gender = self.register_gender.get()
        genre_preference = self.register_genre.get() if user_type == "reader" else None
        
        # Prevent registration as tech support
        if user_type == "tech_support":
            self.show_toast("Tech support accounts cannot be created through registration", "error")
            return
            
        if not email or not username or not password:
            self.show_toast("Please fill in all required fields", "error")
            return
            
        try:
            # Validate date format
            if date_of_birth:
                datetime.strptime(date_of_birth, "%Y-%m-%d")
            
            # Hash the password using the Database class method
            hashed_password = self.db.hash_password(password)
            
            # Generate avatar
            avatar_img = self.generate_avatar_for_user(username, email)
            # Convert image to binary data
            img_byte_arr = io.BytesIO()
            avatar_img.save(img_byte_arr, format='PNG')
            avatar_data = img_byte_arr.getvalue()
            
            # Insert user into database
            self.db.cursor.execute("""
                INSERT INTO users (email, username, password, full_name, user_type, 
                                 date_of_birth, gender, book_genre_preference, avatar)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (email, username, hashed_password, full_name, user_type, 
                  date_of_birth, gender, genre_preference, avatar_data))
            self.db.conn.commit()
            
            self.show_toast("Registration successful!", "success")
            self.show_auth_screen()
            
        except ValueError:
            self.show_toast("Invalid date format. Please use YYYY-MM-DD", "error")
        except sqlite3.IntegrityError:
            self.show_toast("Email already registered", "error")
        except Exception as e:
            self.show_toast(f"Registration failed: {str(e)}", "error")
    
    def show_toast(self, message, message_type="info"):
        """Show a toast notification with an icon based on message type"""
        try:
            # Choose icon based on message type
            if message_type == "error":
                icon = "❌"
            elif message_type == "success":
                icon = "✅"
            elif message_type == "warning":
                icon = "⚠️"
            else:
                icon = "ℹ️"
                
            # Create a new toast notification instead of using toast_manager.show_toast
            ToastNotification(
                title=f"{icon} bookverse Reader",
                message=message,
                duration=3000,
                bootstyle=message_type,
                position=(-10, 50, 'se')
            ).show_toast()
        except Exception as e:
            # Fall back to messagebox if toast fails
            print(f"Toast notification failed: {str(e)}")
            if message_type == "error":
                messagebox.showerror("Error", message)
            elif message_type == "warning":
                messagebox.showwarning("Warning", message)
            else:
                messagebox.showinfo("Information", message)

    def show_main_interface(self):
        # Create main frame
        self.main_frame = ttk.Frame(self.root, style="TFrame")
        self.main_frame.pack(expand=True, fill="both")
        
        # Get username - different handling for tech support vs regular users
        if self.user_type == "tech_support" and hasattr(self, 'tech_support_username'):
            username = self.tech_support_username
        else:
            # Get user information from database
            self.db.cursor.execute('SELECT username FROM users WHERE email = ?', (self.current_user,))
            user_data = self.db.cursor.fetchone()
            
            if user_data is None:
                # User not found in database
                self.show_toast("User account not found. Please try logging in again.", "error")
                # Destroy the main frame
                self.main_frame.destroy()
                # Create new authentication frame
                self.auth_frame = ttk.Frame(self.root, style="Auth.TFrame")
                self.auth_frame.pack(expand=True, fill="both")
                # Show authentication screen
                self.show_auth_screen()
                return
                
            username = user_data[0]
        
        # Create header with welcome message and user info
        header_frame = ttk.Frame(self.main_frame, style="TFrame")
        header_frame.pack(fill="x", padx=10, pady=5)
        
        # Welcome message with username
        welcome_text = f"Welcome back, {username} 🌼"
        welcome_label = ttk.Label(header_frame, 
                                text=welcome_text,
                                font=("Garamond", 18, "bold"),
                                foreground=self.colors["primary"])
        welcome_label.pack(side=tk.LEFT, padx=10)
        
        # Theme toggle button
        theme_btn = tk.Button(header_frame,
                            text="☀ / ☽",
                            command=self.toggle_theme,
                            bg=self.colors["button_secondary"],
                            fg="white",
                            font=("Quicksand", 10),
                            relief=tk.FLAT,
                            padx=10,
                            pady=5,
                            cursor="hand2")
        theme_btn.pack(side=tk.RIGHT, padx=10)
        
        # Removed menu bar code - all menu functionality is now in tabs
        
        # Show appropriate interface based on user type
        if self.user_type == "reader":
            self.show_reader_interface()
        elif self.user_type == "author":
            self.show_author_interface()
        elif self.user_type == "tech_support":
            self.show_tech_support_interface()

    def show_reader_interface(self):
        # Create notebook for tabs with a nicer style
        self.notebook = ttk.Notebook(self.main_frame)
        self.notebook.pack(expand=True, fill="both", padx=10, pady=10)
        
        # Create content frame for each tab
        self.content_frame = tk.Frame(self.notebook, bg=self.colors["background"])
        self.library_frame = tk.Frame(self.notebook, bg=self.colors["background"])
        self.discussions_frame = tk.Frame(self.notebook, bg=self.colors["background"])
        self.reviews_frame = tk.Frame(self.notebook, bg=self.colors["background"])
        self.profile_frame = tk.Frame(self.notebook, bg=self.colors["background"])
        
        # Add the frames to the notebook with icons
        self.notebook.add(self.content_frame, text="Browse Books", image=self.images["book"], compound=tk.LEFT)
        self.notebook.add(self.library_frame, text="My Library", image=self.images["bookmark"], compound=tk.LEFT)
        self.notebook.add(self.discussions_frame, text="Discussions", compound=tk.LEFT)
        self.notebook.add(self.reviews_frame, text="My Reviews", compound=tk.LEFT)
        self.notebook.add(self.profile_frame, text="Profile", compound=tk.LEFT)
        
        # Setup each tab
        print("Setting up browse tab...")
        self.setup_browse_tab()
        
        print("Setting up library tab...")
        self.setup_library_tab()
        
        print("Setting up discussions tab...")
        self.setup_reader_discussions_tab()
        
        print("Setting up reviews tab...")
        self.setup_reader_reviews_tab()
        
        print("Setting up profile tab...")
        self.setup_reader_profile_tab()
        
        # Show browse tab by default
        self.notebook.select(0)
        
    def setup_reader_reviews_tab(self):
        # Clear existing content
        for widget in self.reviews_frame.winfo_children():
            widget.destroy()
        
        # Create background canvas with gradient
        canvas = tk.Canvas(self.reviews_frame, bg=self.colors["background"],
                         highlightthickness=0)
        canvas.pack(fill="both", expand=True)
        
        # Draw gradient background
        self.draw_gradient_background(canvas, 1024, 768, 
                                   self.colors["background_gradient"][0], 
                                   self.colors["background_gradient"][1])
        
        # Create main content frame
        main_content = tk.Frame(canvas, bg=self.colors["background"])
        main_content.pack(pady=20, fill="both", expand=True)
        
        # Create title
        title_label = tk.Label(main_content,
                            text="My Reviews",
                            font=("Garamond", 20, "bold"),
                            fg=self.colors["primary"],
                            bg=self.colors["background"])
        title_label.pack(pady=10)
        
        # Get user's reviews
        self.db.cursor.execute('''
            SELECT r.book_id, r.rating, r.comment, r.review_date, b.title
            FROM reviews r
            JOIN books b ON r.book_id = b.id
            WHERE r.user_email = ?
            ORDER BY r.review_date DESC
        ''', (self.current_user,))
        
        reviews = self.db.cursor.fetchall()
        
        # Reviews container with scrollbar
        reviews_container = tk.Frame(main_content, bg=self.colors["background"])
        reviews_container.pack(fill="both", expand=True, padx=20, pady=10)
        
        # Create scrollbar
        scrollbar = ttk.Scrollbar(reviews_container)
        scrollbar.pack(side=tk.RIGHT, fill="y")
        
        reviews_canvas = tk.Canvas(reviews_container,
                                 yscrollcommand=scrollbar.set,
                                 bg=self.colors["background"],
                                 highlightthickness=0)
        reviews_canvas.pack(side=tk.LEFT, fill="both", expand=True)
        
        scrollbar.config(command=reviews_canvas.yview)
        
        reviews_frame = tk.Frame(reviews_canvas, bg=self.colors["background"])
        
        # Set reasonable default width
        canvas_width = reviews_canvas.winfo_width()
        if canvas_width < 100:
            canvas_width = 800
        
        window_id = reviews_canvas.create_window((0, 0), window=reviews_frame, 
                                            anchor="nw", width=canvas_width)
        
        # Configure the canvas for scrolling
        def configure_reviews_canvas(event):
            reviews_canvas.configure(scrollregion=reviews_canvas.bbox("all"))
            canvas_width = reviews_canvas.winfo_width()
            if canvas_width > 100:
                reviews_canvas.itemconfig(window_id, width=canvas_width)
        
        reviews_canvas.bind("<Configure>", configure_reviews_canvas)
        reviews_frame.bind("<Configure>", configure_reviews_canvas)
        
        if not reviews:
            no_reviews_label = tk.Label(reviews_frame,
                                     text="You haven't reviewed any books yet.",
                                     font=("Garamond", 14, "italic"),
                                     fg=self.colors["text"],
                                     bg=self.colors["background"])
            no_reviews_label.pack(pady=20)
        else:
            for book_id, rating, comment, review_date, book_title in reviews:
                review_card = tk.Frame(reviews_frame, 
                                    bg=self.colors["card_bg"],
                                    highlightbackground=self.colors["card_shadow"],
                                    highlightthickness=1)
                review_card.pack(fill="x", padx=10, pady=10)
                
                # Book title
                book_title_label = tk.Label(review_card,
                                         text=book_title,
                                         font=("Garamond", 16, "bold"),
                                         fg=self.colors["primary"],
                                         bg=self.colors["card_bg"])
                book_title_label.pack(anchor="w", padx=15, pady=(15, 5))
                
                # Rating with stars
                rating_frame = tk.Frame(review_card, bg=self.colors["card_bg"])
                rating_frame.pack(anchor="w", padx=15, pady=5)
                
                # Convert rating to stars
                stars = "★" * rating + "☆" * (5 - rating)
                
                rating_label = tk.Label(rating_frame,
                                      text=f"Rating: {stars}",
                                      font=("Garamond", 12),
                                      fg=self.colors["accent"],
                                      bg=self.colors["card_bg"])
                rating_label.pack(side=tk.LEFT)
                
                # Date
                date_label = tk.Label(rating_frame,
                                    text=f"Posted on: {review_date}",
                                    font=("Garamond", 10),
                                    fg=self.colors["light_text"],
                                    bg=self.colors["card_bg"])
                date_label.pack(side=tk.RIGHT, padx=15)
                
                # Review content
                comment_label = tk.Label(review_card,
                                       text=comment,
                                       wraplength=600,
                                       font=("Garamond", 12),
                                       fg=self.colors["text"],
                                       bg=self.colors["card_bg"])
                comment_label.pack(anchor="w", padx=15, pady=(5, 15))
                
                # Button to view the book
                btn_frame = tk.Frame(review_card, bg=self.colors["card_bg"])
                btn_frame.pack(anchor="e", padx=15, pady=(0, 15))
                
                view_book_btn = self.create_rounded_button(btn_frame, 
                                                        "View Book", 
                                                        lambda t=book_title: self.view_book(t))
                view_book_btn.pack(side=tk.RIGHT)
        
        # Configure the canvas scrolling
        reviews_frame.update_idletasks()
        reviews_canvas.config(scrollregion=reviews_canvas.bbox("all"))

    def setup_browse_tab(self):
        # Clear existing content
        for widget in self.content_frame.winfo_children():
            widget.destroy()
        
        # Create background canvas with gradient
        canvas = tk.Canvas(self.content_frame, bg=self.colors["background"],
                         highlightthickness=0)
        canvas.pack(fill="both", expand=True)
        
        # Draw gradient background
        self.draw_gradient_background(canvas, 1024, 768, 
                                   self.colors["background_gradient"][0], 
                                   self.colors["background_gradient"][1])
        
        # Create main content frame
        main_content = ttk.Frame(canvas, style="TFrame")
        main_content.pack(pady=20, fill="both", expand=True)
        
        # Search frame with rounded corners
        search_frame = ttk.Frame(main_content, style="Card.TFrame")
        search_frame.pack(fill="x", padx=20, pady=10)
        
        # Apply shadow effect
        self.apply_shadow_effect(search_frame)
        
        search_title = ttk.Label(search_frame,
                              text="Discover Your Next Adventure",
                              font=("Garamond", 16, "bold"),
                              foreground=self.colors["primary"],
                              background=self.colors["card_bg"])
        search_title.pack(pady=(10, 5))
        
        search_container = ttk.Frame(search_frame, style="Card.TFrame")
        search_container.pack(padx=20, pady=10, fill="x")
        
        self.search_var = tk.StringVar()
        search_entry = ttk.Entry(search_container, textvariable=self.search_var, 
                               width=40, font=("Quicksand", 12))
        search_entry.pack(side=tk.LEFT, padx=5, fill="x", expand=True)
        
        search_btn = self.create_rounded_button(search_container, "Search", 
                                             lambda: self.search_books(self.content_frame))
        search_btn.pack(side=tk.LEFT, padx=5)
        
        # Books display frame with scrollbar
        books_container = ttk.Frame(main_content)
        books_container.pack(fill="both", expand=True, padx=20, pady=10)
        
        # Create scrollable frame for books
        scrollbar = ttk.Scrollbar(books_container, orient="vertical", style="Custom.Vertical.TScrollbar")
        scrollbar.pack(side=tk.RIGHT, fill="y")
        
        books_canvas = tk.Canvas(books_container, 
                              bg=self.colors["background"], 
                              highlightthickness=0,
                              height=500,  # Explicit height
                              yscrollcommand=scrollbar.set)
        books_canvas.pack(side=tk.LEFT, fill="both", expand=True)
        
        scrollbar.config(command=books_canvas.yview)
        
        # Create a frame to hold all the books - use tk.Frame instead of ttk.Frame for background
        self.books_frame = tk.Frame(books_canvas, bg=self.colors["background"])
        
        # Force the frame to have a minimum width that makes the books visible
        canvas_width = books_canvas.winfo_width()
        if canvas_width < 100:  # If canvas is not yet properly sized
            canvas_width = 800  # Use a reasonable default width
        
        window_id = books_canvas.create_window((0, 0), window=self.books_frame, anchor="nw", width=canvas_width)
        
        # Configure the canvas for scrolling
        def configure_books_canvas(event):
            books_canvas.configure(scrollregion=books_canvas.bbox("all"))
            # Update the width of the books_frame to match the canvas width
            canvas_width = books_canvas.winfo_width()
            if canvas_width > 100:  # Only update if we have a reasonable width
                books_canvas.itemconfig(window_id, width=canvas_width)
            
        books_canvas.bind("<Configure>", configure_books_canvas)
        self.books_frame.bind("<Configure>", configure_books_canvas)
        
        # Debug - check if we have any books in the database
        self.db.cursor.execute("SELECT COUNT(*) FROM books")
        book_count = self.db.cursor.fetchone()[0]
        print(f"DEBUG: Found {book_count} books in database")
        
        # Display all books
        self.display_all_books()
        
        # Debug - check if books were displayed
        books_added = len(self.books_frame.winfo_children())
        print(f"DEBUG: Added {books_added} book widgets to the UI")

    def display_all_books(self):
        # Clear existing books
        for widget in self.books_frame.winfo_children():
            widget.destroy()
        
        try:
            # Get all books from database
            self.db.cursor.execute('''
                SELECT b.id, b.title, b.description, u.username, b.amazon_link, u.avatar
                FROM books b
                JOIN users u ON b.author_email = u.email
            ''')
            books = self.db.cursor.fetchall()
            
            print(f"DEBUG: SQL query returned {len(books)} books")
            
            # If no books found
            if not books:
                no_books_label = tk.Label(self.books_frame,
                                      text="No books found.",
                                      font=("Garamond", 14, "italic"),
                                      fg=self.colors["text"],
                                      bg=self.colors["background"])
                no_books_label.pack(pady=20)
                return
            
            # Create a container for books - using grid layout
            books_grid = tk.Frame(self.books_frame, bg=self.colors["background"])
            books_grid.pack(fill="both", expand=True, padx=10, pady=10)
            
            # Configure the grid to have 3 columns of equal width
            for i in range(3):
                books_grid.columnconfigure(i, weight=1)
            
            # Display books in a grid with cards
            book_count = 0
            for i, (book_id, title, description, author, amazon_link, author_avatar) in enumerate(books):
                try:
                    # Create a card frame for each book
                    book_card = tk.Frame(books_grid, bg=self.colors["card_bg"], 
                                      highlightbackground=self.colors["card_shadow"],
                                      highlightthickness=1,
                                      width=300, height=350)
                    book_card.grid(row=i//3, column=i%3, padx=10, pady=10, sticky="nsew")
                    
                    # Prevent widget from shrinking below minimum size
                    book_card.grid_propagate(False)
                    
                    # Book title
                    title_label = tk.Label(book_card,
                                        text=title,
                                        font=("Garamond", 16, "bold"),
                                        fg=self.colors["primary"],
                                        bg=self.colors["card_bg"])
                    title_label.pack(pady=(15, 5), padx=15)
                    
                    # Author with avatar
                    author_frame = tk.Frame(book_card, bg=self.colors["card_bg"])
                    author_frame.pack(pady=5, padx=15, fill="x")
                    
                    # Author avatar
                    if author_avatar:
                        try:
                            avatar_img = Image.open(io.BytesIO(author_avatar))
                            avatar_img = avatar_img.resize((24, 24))
                            avatar_photo = ImageTk.PhotoImage(avatar_img)
                            avatar_label = tk.Label(author_frame, image=avatar_photo, bg=self.colors["card_bg"])
                            avatar_label.image = avatar_photo  # Keep a reference to prevent garbage collection
                            avatar_label.pack(side=tk.LEFT, padx=(0, 5))
                        except Exception as e:
                            print(f"Error displaying avatar for {title}: {e}")
                            # Fall back to text if image loading fails
                    
                    author_label = tk.Label(author_frame,
                                         text=f"by {author}",
                                         font=("Garamond", 12, "italic"),
                                         fg=self.colors["text"],
                                         bg=self.colors["card_bg"])
                    author_label.pack(side=tk.LEFT)
                    
                    # Description - truncate if too long
                    short_desc = description
                    if len(description) > 100:
                        short_desc = description[:100] + "..."
                        
                    desc_label = tk.Label(book_card,
                                       text=short_desc,
                                       wraplength=250,
                                       font=("Quicksand", 10),
                                       fg=self.colors["text"],
                                       bg=self.colors["card_bg"])
                    desc_label.pack(pady=10, padx=15, fill="x")
                    
                    # Buttons container
                    btn_frame = tk.Frame(book_card, bg=self.colors["card_bg"])
                    btn_frame.pack(pady=10, padx=15, fill="x")
                    
                    # View/Read button
                    view_btn = self.create_rounded_button(btn_frame, "Read", lambda t=title: self.view_book(t))
                    view_btn.pack(side=tk.LEFT, padx=2)
                    
                    # Add to library button
                    add_btn = self.create_rounded_button(btn_frame, "Add", lambda t=title: self.add_to_library(t), primary=False)
                    add_btn.pack(side=tk.LEFT, padx=2)
                    
                    # Buy on Amazon button (if link available)
                    if amazon_link:
                        amazon_btn = tk.Button(btn_frame,
                                            text="Amazon",
                                            command=lambda l=amazon_link: self.open_amazon_link(l),
                                            bg="#FF9900",  # Amazon orange
                                            fg="white",
                                            font=("Quicksand", 10),
                                            relief=tk.FLAT,
                                            borderwidth=0,
                                            padx=10,
                                            pady=5,
                                            cursor="hand2")
                        amazon_btn.pack(side=tk.LEFT, padx=2)
                    
                    # Second row of buttons
                    btn_frame2 = tk.Frame(book_card, bg=self.colors["card_bg"])
                    btn_frame2.pack(pady=(0, 10), padx=15, fill="x")
                    
                    # Review button
                    review_btn = self.create_rounded_button(btn_frame2, "Reviews", 
                                                         lambda t=title: self.view_reviews(t), primary=False)
                    review_btn.pack(side=tk.LEFT, padx=2)
                    
                    # Discussion button
                    discussion_btn = self.create_rounded_button(btn_frame2, "Discussions", 
                                                             lambda t=title: self.view_book_discussions(t), primary=False)
                    discussion_btn.pack(side=tk.LEFT, padx=2)
                    
                    book_count += 1
                except Exception as e:
                    print(f"Error creating book card for {title}: {e}")
            
            print(f"DEBUG: Successfully created {book_count} book cards")
            
            # Update the display after creating all books
            self.books_frame.update_idletasks()
        
        except Exception as e:
            print(f"ERROR in display_all_books: {e}")
            import traceback
            traceback.print_exc()
            
            error_label = tk.Label(self.books_frame,
                                 text=f"Error loading books: {str(e)}",
                                 font=("Garamond", 14, "italic"),
                                 fg="red",
                                 bg=self.colors["background"])
            error_label.pack(pady=20)

    def search_books(self, parent):
        search_term = self.search_var.get().lower()
        
        # Clear existing books
        for widget in self.books_frame.winfo_children():
            widget.destroy()
        
        # Get matching books from database
        self.db.cursor.execute('''
            SELECT b.title, b.description, u.username, b.amazon_link, u.avatar
            FROM books b
            JOIN users u ON b.author_email = u.email
            WHERE LOWER(b.title) LIKE ? OR LOWER(b.description) LIKE ? OR LOWER(u.username) LIKE ?
        ''', (f'%{search_term}%', f'%{search_term}%', f'%{search_term}%'))
        
        books = self.db.cursor.fetchall()
        
        # Show a message if no books found
        if not books:
            no_results = ttk.Label(self.books_frame, 
                                 text=f"No books found matching '{search_term}'", 
                                 font=("Garamond", 14, "italic"),
                                 foreground=self.colors["text"])
            no_results.pack(pady=20)
            return
        
        # Create a container for books - using grid layout
        books_grid = ttk.Frame(self.books_frame)
        books_grid.pack(fill="both", expand=True, padx=10, pady=10)
        
        # Configure the grid to have 3 columns of equal width
        for i in range(3):
            books_grid.columnconfigure(i, weight=1)
        
        # Display books in a grid with cards
        for i, (title, description, author, amazon_link, author_avatar) in enumerate(books):
            # Create a card frame for each book
            book_card = ttk.Frame(books_grid, style="Card.TFrame")
            book_card.grid(row=i//3, column=i%3, padx=10, pady=10, sticky="nsew")
            
            # Apply shadow effect
            self.apply_shadow_effect(book_card)
            
            # Book title
            title_label = ttk.Label(book_card,
                                  text=title,
                                  font=("Garamond", 16, "bold"),
                                  foreground=self.colors["primary"],
                                  background=self.colors["card_bg"])
            title_label.pack(pady=(15, 5), padx=15)
            
            # Author with avatar
            author_frame = ttk.Frame(book_card, style="Card.TFrame")
            author_frame.pack(pady=5, padx=15, fill="x")
            
            # Author avatar
            if author_avatar:
                try:
                    avatar_img = Image.open(io.BytesIO(author_avatar))
                    avatar_img = avatar_img.resize((24, 24))
                    avatar_photo = ImageTk.PhotoImage(avatar_img)
                    avatar_label = ttk.Label(author_frame, image=avatar_photo, background=self.colors["card_bg"])
                    avatar_label.image = avatar_photo  # Keep a reference to prevent garbage collection
                    avatar_label.pack(side=tk.LEFT, padx=(0, 5))
                except Exception:
                    # Fall back to text if image loading fails
                    pass
            
            author_label = ttk.Label(author_frame,
                                   text=f"by {author}",
                                   font=("Garamond", 12, "italic"),
                                   foreground=self.colors["text"],
                                   background=self.colors["card_bg"])
            author_label.pack(side=tk.LEFT)
            
            # Description - truncate if too long
            short_desc = description
            if len(description) > 100:
                short_desc = description[:100] + "..."
                
            desc_label = ttk.Label(book_card,
                                 text=short_desc,
                                 wraplength=250,
                                 font=("Quicksand", 10),
                                 foreground=self.colors["text"],
                                 background=self.colors["card_bg"])
            desc_label.pack(pady=10, padx=15, fill="x")
            
            # Buttons container
            btn_frame = ttk.Frame(book_card, style="Card.TFrame")
            btn_frame.pack(pady=10, padx=15, fill="x")
            
            # View/Read button
            view_btn = self.create_rounded_button(btn_frame, "Read", lambda t=title: self.view_book(t))
            view_btn.pack(side=tk.LEFT, padx=2)
            
            # Add to library button
            add_btn = self.create_rounded_button(btn_frame, "Add", lambda t=title: self.add_to_library(t), primary=False)
            add_btn.pack(side=tk.LEFT, padx=2)
            
            # Buy on Amazon button (if link available)
            if amazon_link:
                amazon_btn = tk.Button(btn_frame,
                                     text="Amazon",
                                     command=lambda l=amazon_link: self.open_amazon_link(l),
                                     bg="#FF9900",  # Amazon orange
                                     fg="white",
                                     font=("Quicksand", 10),
                                     relief=tk.FLAT,
                                     borderwidth=0,
                                     padx=10,
                                     pady=5,
                                     cursor="hand2")
                amazon_btn.pack(side=tk.LEFT, padx=2)
            
            # Second row of buttons
            btn_frame2 = ttk.Frame(book_card, style="Card.TFrame")
            btn_frame2.pack(pady=(0, 10), padx=15, fill="x")
            
            # Review button
            review_btn = self.create_rounded_button(btn_frame2, "Reviews", 
                                                 lambda t=title: self.view_reviews(t), primary=False)
            review_btn.pack(side=tk.LEFT, padx=2)
            
            # Discussion button
            discussion_btn = self.create_rounded_button(btn_frame2, "Discussions", 
                                                     lambda t=title: self.view_book_discussions(t), primary=False)
            discussion_btn.pack(side=tk.LEFT, padx=2)

    def view_book(self, book_name):
        # Get book information including PDF data
        self.db.cursor.execute('''
            SELECT b.pdf_data, b.description, u.username, b.id
            FROM books b
            JOIN users u ON b.author_email = u.email
            WHERE b.title = ?
        ''', (book_name,))
        result = self.db.cursor.fetchone()
        
        if not result:
            self.show_toast(f"Book not found: {book_name}", "error")
            return
            
        pdf_data, description, author, book_id = result
        
        try:
            # Show loading indicator
            self.show_toast(f"Opening {book_name}", "info")
            
            # Create a temporary PDF file
            import tempfile
            import os
            temp_dir = tempfile.gettempdir()
            temp_pdf_path = os.path.join(temp_dir, f"{book_name}.pdf")
            
            # Write PDF data to temporary file
            with open(temp_pdf_path, 'wb') as temp_file:
                temp_file.write(pdf_data)
            
            # Open PDF in default PDF viewer
            webbrowser.open(temp_pdf_path)
            
            # Update last read timestamp for readers
            if self.user_type == "reader":
                # Update last read timestamp
                self.db.cursor.execute('''
                    INSERT OR REPLACE INTO user_library (user_email, book_id, last_read)
                    VALUES (?, ?, CURRENT_TIMESTAMP)
                ''', (self.current_user, book_id))
                
                # Increment books_read count if this is the first time reading
                self.db.cursor.execute('''
                    SELECT COUNT(*) FROM user_library 
                    WHERE user_email = ? AND book_id = ? AND last_read IS NOT NULL
                ''', (self.current_user, book_id))
                
                if self.db.cursor.fetchone()[0] <= 1:
                    self.db.cursor.execute('''
                        UPDATE users
                        SET books_read = COALESCE(books_read, 0) + 1
                        WHERE email = ?
                    ''', (self.current_user,))
                
                # Update reading streak
                current_date = datetime.now().strftime("%Y-%m-%d")
                
                self.db.cursor.execute('''
                    SELECT MAX(last_read) FROM user_library
                    WHERE user_email = ? AND last_read < ?
                ''', (self.current_user, current_date))
                
                last_activity = self.db.cursor.fetchone()[0]
                
                if last_activity:
                    # Format as date for comparison
                    last_date = datetime.strptime(last_activity.split()[0], "%Y-%m-%d").date()
                    today = datetime.now().date()
                    
                    # If the last activity was yesterday, increment streak
                    if (today - last_date).days == 1:
                        self.db.cursor.execute('''
                            UPDATE users
                            SET reading_streak = COALESCE(reading_streak, 0) + 1
                            WHERE email = ?
                        ''', (self.current_user,))
                else:
                    # First reading activity, set streak to 1
                    self.db.cursor.execute('''
                        UPDATE users
                        SET reading_streak = 1
                        WHERE email = ?
                    ''', (self.current_user,))
                
                # Check for badges
                self.check_for_badges(book_id)
                
                # Commit all changes
                self.db.conn.commit()
                
        except Exception as e:
            self.show_toast(f"Could not open PDF file: {str(e)}", "error")
    
    def check_for_badges(self, book_id):
        """Check and award badges based on user activity"""
        try:
            # Get current counts
            self.db.cursor.execute('''
                SELECT books_read, reading_streak
                FROM users
                WHERE email = ?
            ''', (self.current_user,))
            
            books_read, reading_streak = self.db.cursor.fetchone()
            
            # Check for reading badges
            if books_read >= 5 and not self.has_badge("reader", "bookverse"):
                self.award_badge("reader", "BookVerse", "Read 5 books")
            
            if books_read >= 10 and not self.has_badge("reader", "Bibliophile"):
                self.award_badge("reader", "Bibliophile", "Read 10 books")
            
            # Check for streak badges
            if reading_streak >= 3 and not self.has_badge("reader", "Consistent Reader"):
                self.award_badge("reader", "Consistent Reader", "3-day reading streak")
            
            if reading_streak >= 7 and not self.has_badge("reader", "Dedicated Reader"):
                self.award_badge("reader", "Dedicated Reader", "7-day reading streak")
            
            # Check for review badges
            self.db.cursor.execute('''
                SELECT COUNT(*) FROM reviews
                WHERE user_email = ?
            ''', (self.current_user,))
            
            review_count = self.db.cursor.fetchone()[0]
            
            if review_count >= 3 and not self.has_badge("reviewer", "Reviewer"):
                self.award_badge("reviewer", "Reviewer", "Posted 3 reviews")
            
            if review_count >= 10 and not self.has_badge("reviewer", "Critic"):
                self.award_badge("reviewer", "Critic", "Posted 10 reviews")
            
        except Exception as e:
            print(f"Error checking for badges: {str(e)}")
    
    def has_badge(self, badge_type, badge_name):
        """Check if user already has a specific badge"""
        self.db.cursor.execute('''
            SELECT COUNT(*) FROM user_badges
            WHERE user_email = ? AND badge_type = ? AND badge_name = ?
        ''', (self.current_user, badge_type, badge_name))
        
        return self.db.cursor.fetchone()[0] > 0
    
    def award_badge(self, badge_type, badge_name, description=""):
        """Award a badge to the user and show a notification"""
        try:
            self.db.cursor.execute('''
                INSERT INTO user_badges (user_email, badge_type, badge_name)
                VALUES (?, ?, ?)
            ''', (self.current_user, badge_type, badge_name))
            
            self.db.conn.commit()
            
            # Show a special toast notification for badge
            self.show_toast(f"🎉 New Achievement: {badge_name}!", "success")
            
        except Exception as e:
            print(f"Error awarding badge: {str(e)}")

    def add_to_library(self, book_name):
        try:
            # Get book ID
            self.db.cursor.execute('SELECT id FROM books WHERE title = ?', (book_name,))
            book_id = self.db.cursor.fetchone()[0]
            
            # Check if already in library
            self.db.cursor.execute('''
                SELECT COUNT(*) FROM user_library
                WHERE user_email = ? AND book_id = ?
            ''', (self.current_user, book_id))
            
            count = self.db.cursor.fetchone()[0]
            
            if count > 0:
                self.show_toast("Book already in your library", "info")
                return
            
            # Add to library
            self.db.cursor.execute('''
                INSERT INTO user_library (user_email, book_id)
                VALUES (?, ?)
            ''', (self.current_user, book_id))
            self.db.conn.commit()
            
            self.show_toast(f"Added {book_name} to your library", "success")
        
        except sqlite3.IntegrityError:
            self.show_toast("Book already in your library", "info")
        except Exception as e:
            self.show_toast(f"Error: {str(e)}", "error")

    def open_amazon_link(self, link):
        if not link:
            self.show_toast("No Amazon link available for this book", "warning")
            return
            
        # Check if the link is properly formatted with http/https
        if not link.startswith('http://') and not link.startswith('https://'):
            link = 'https://' + link
        
        try:
            import webbrowser
            webbrowser.open(link)
            self.show_toast("Opening Amazon link in browser", "info")
        except Exception as e:
            self.show_toast(f"Error opening link: {str(e)}", "error")

    def setup_library_tab(self):
        # Clear existing content
        for widget in self.library_frame.winfo_children():
            widget.destroy()
        
        # Create background canvas with gradient
        canvas = tk.Canvas(self.library_frame, bg=self.colors["background"],
                         highlightthickness=0)
        canvas.pack(fill="both", expand=True)
        
        # Draw gradient background
        self.draw_gradient_background(canvas, 1024, 768, 
                                   self.colors["background_gradient"][0], 
                                   self.colors["background_gradient"][1])
        
        # Create main content frame
        main_content = tk.Frame(canvas, bg=self.colors["background"])
        main_content.pack(pady=20, fill="both", expand=True)
        
        # Add title
        title_frame = tk.Frame(main_content, bg=self.colors["background"])
        title_frame.pack(fill="x", padx=20, pady=10)
        
        title_label = tk.Label(title_frame,
                            text="My Reading Library",
                            font=("Garamond", 20, "bold"),
                            fg=self.colors["primary"],
                            bg=self.colors["background"])
        title_label.pack(side=tk.LEFT)
        
        # Create a refresh button
        refresh_btn = self.create_rounded_button(title_frame, "Refresh", self.display_library_books)
        refresh_btn.pack(side=tk.RIGHT, padx=10)
        
        # Books display frame with scrollbar
        books_container = tk.Frame(main_content, bg=self.colors["background"])
        books_container.pack(fill="both", expand=True, padx=20, pady=10)
        
        # Create scrollable frame for books
        scrollbar = ttk.Scrollbar(books_container, orient="vertical", style="Custom.Vertical.TScrollbar")
        scrollbar.pack(side=tk.RIGHT, fill="y")
        
        library_canvas = tk.Canvas(books_container, 
                                bg=self.colors["background"], 
                                highlightthickness=0,
                                height=500,  # Explicit height
                                yscrollcommand=scrollbar.set)
        library_canvas.pack(side=tk.LEFT, fill="both", expand=True)
        
        scrollbar.config(command=library_canvas.yview)
        
        # Create a frame to hold all the books
        self.library_books_frame = tk.Frame(library_canvas, bg=self.colors["background"])
        
        # Set reasonable default width
        canvas_width = library_canvas.winfo_width()
        if canvas_width < 100:
            canvas_width = 800
        
        window_id = library_canvas.create_window((0, 0), window=self.library_books_frame, 
                                              anchor="nw", width=canvas_width)
        
        # Configure the canvas for scrolling
        def configure_library_canvas(event):
            library_canvas.configure(scrollregion=library_canvas.bbox("all"))
            canvas_width = library_canvas.winfo_width()
            if canvas_width > 100:
                library_canvas.itemconfig(window_id, width=canvas_width)
            
        library_canvas.bind("<Configure>", configure_library_canvas)
        self.library_books_frame.bind("<Configure>", configure_library_canvas)
        
        # Display user's library books
        self.display_library_books()

    def display_library_books(self):
        # Clear existing books
        for widget in self.library_books_frame.winfo_children():
            widget.destroy()
        
        try:
            # Get books from user's library
            self.db.cursor.execute('''
                SELECT b.id, b.title, b.description, u.username, b.amazon_link, u.avatar, ul.last_read
                FROM user_library ul
                JOIN books b ON ul.book_id = b.id
                JOIN users u ON b.author_email = u.email
                WHERE ul.user_email = ?
                ORDER BY ul.last_read DESC
            ''', (self.current_user,))
            
            books = self.db.cursor.fetchall()
            
            # If no books found
            if not books:
                no_books_label = tk.Label(self.library_books_frame,
                                      text="Your library is empty. Add books from the Browse tab!",
                                      font=("Garamond", 14, "italic"),
                                      fg=self.colors["text"],
                                      bg=self.colors["background"])
                no_books_label.pack(pady=20)
                return
            
            # Create a container for books - using grid layout
            books_grid = tk.Frame(self.library_books_frame, bg=self.colors["background"])
            books_grid.pack(fill="both", expand=True, padx=10, pady=10)
            
            # Configure the grid to have 3 columns of equal width
            for i in range(3):
                books_grid.columnconfigure(i, weight=1)
            
            # Display books in a grid with cards
            book_count = 0
            for i, (book_id, title, description, author, amazon_link, author_avatar, last_read) in enumerate(books):
                try:
                    # Create a card frame for each book
                    book_card = tk.Frame(books_grid, bg=self.colors["card_bg"], 
                                      highlightbackground=self.colors["card_shadow"],
                                      highlightthickness=1,
                                      width=300, height=400)
                    book_card.grid(row=i//3, column=i%3, padx=10, pady=10, sticky="nsew")
                    book_card.grid_propagate(False)
                    
                    # Book title
                    title_label = tk.Label(book_card,
                                        text=title,
                                        font=("Garamond", 16, "bold"),
                                        fg=self.colors["primary"],
                                        bg=self.colors["card_bg"])
                    title_label.pack(pady=(15, 5), padx=15)
                    
                    # Author with avatar
                    author_frame = tk.Frame(book_card, bg=self.colors["card_bg"])
                    author_frame.pack(pady=5, padx=15, fill="x")
                    
                    # Author avatar
                    if author_avatar:
                        try:
                            avatar_img = Image.open(io.BytesIO(author_avatar))
                            avatar_img = avatar_img.resize((24, 24))
                            avatar_photo = ImageTk.PhotoImage(avatar_img)
                            avatar_label = tk.Label(author_frame, image=avatar_photo, bg=self.colors["card_bg"])
                            avatar_label.image = avatar_photo  # Keep a reference to prevent garbage collection
                            avatar_label.pack(side=tk.LEFT, padx=(0, 5))
                        except Exception:
                            # Fall back to text if image loading fails
                            pass
                    
                    author_label = tk.Label(author_frame,
                                         text=f"by {author}",
                                         font=("Garamond", 12, "italic"),
                                         fg=self.colors["text"],
                                         bg=self.colors["card_bg"])
                    author_label.pack(side=tk.LEFT)
                    
                    # Last read date if available
                    if last_read:
                        last_read_label = tk.Label(book_card,
                                               text=f"Last read: {last_read}",
                                               font=("Quicksand", 10),
                                               fg=self.colors["light_text"],
                                               bg=self.colors["card_bg"])
                        last_read_label.pack(pady=(2, 5), padx=15)
                    
                    # Description - truncate if too long
                    short_desc = description
                    if len(description) > 100:
                        short_desc = description[:100] + "..."
                        
                    desc_label = tk.Label(book_card,
                                       text=short_desc,
                                       wraplength=250,
                                       font=("Quicksand", 10),
                                       fg=self.colors["text"],
                                       bg=self.colors["card_bg"])
                    desc_label.pack(pady=10, padx=15, fill="x")
                    
                    # Buttons container
                    btn_frame = tk.Frame(book_card, bg=self.colors["card_bg"])
                    btn_frame.pack(pady=10, padx=15, fill="x")
                    
                    # View/Read button
                    view_btn = self.create_rounded_button(btn_frame, "Read", lambda t=title: self.view_book(t))
                    view_btn.pack(side=tk.LEFT, padx=2)
                    
                    # Remove from library button
                    remove_btn = self.create_rounded_button(btn_frame, "Remove", 
                                                        lambda t=title: self.remove_from_library(t), 
                                                        primary=False)
                    remove_btn.pack(side=tk.LEFT, padx=2)
                    
                    # Buy on Amazon button (if link available)
                    if amazon_link:
                        amazon_btn = tk.Button(btn_frame,
                                           text="Amazon",
                                           command=lambda l=amazon_link: self.open_amazon_link(l),
                                           bg="#FF9900",  # Amazon orange
                                           fg="white",
                                           font=("Quicksand", 10),
                                           relief=tk.FLAT,
                                           borderwidth=0,
                                           padx=10,
                                           pady=5,
                                           cursor="hand2")
                        amazon_btn.pack(side=tk.LEFT, padx=2)
                    
                    # Second row of buttons
                    btn_frame2 = tk.Frame(book_card, bg=self.colors["card_bg"])
                    btn_frame2.pack(pady=(0, 10), padx=15, fill="x")
                    
                    # Review button
                    review_btn = self.create_rounded_button(btn_frame2, "Reviews", 
                                                         lambda t=title: self.view_reviews(t), 
                                                         primary=False)
                    review_btn.pack(side=tk.LEFT, padx=2)
                    
                    # Discussion button
                    discussion_btn = self.create_rounded_button(btn_frame2, "Discussions", 
                                                             lambda t=title: self.view_book_discussions(t), 
                                                             primary=False)
                    discussion_btn.pack(side=tk.LEFT, padx=2)
                    
                    book_count += 1
                except Exception as e:
                    print(f"Error displaying library book {title}: {e}")
            
            print(f"DEBUG: Successfully displayed {book_count} library books")
        
        except Exception as e:
            print(f"ERROR in display_library_books: {e}")
            error_label = tk.Label(self.library_books_frame,
                                text=f"Error loading library: {str(e)}",
                                font=("Garamond", 14, "italic"),
                                fg="red",
                                bg=self.colors["background"])
            error_label.pack(pady=20)

    def remove_from_library(self, book_name):
        self.db.cursor.execute('''
            DELETE FROM user_library
            WHERE user_email = ? AND book_id = (SELECT id FROM books WHERE title = ?)
        ''', (self.current_user, book_name))
        self.db.conn.commit()
        self.display_library_books()
        self.show_toast(f"Removed {book_name} from your library", "info")

    def setup_reader_discussions_tab(self):
        # Clear existing content
        for widget in self.discussions_frame.winfo_children():
            widget.destroy()
        
        # Title
        title_label = ttk.Label(self.discussions_frame, text="Book Discussions", font=("Segoe UI", 16, "bold"))
        title_label.pack(pady=10)
        
        # Create a container for discussions
        discussions_container = ttk.Frame(self.discussions_frame)
        discussions_container.pack(fill="both", expand=True, padx=10, pady=10)
        
        # Add scrollbar
        scrollbar = ttk.Scrollbar(discussions_container)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        # Create canvas for discussions
        canvas = tk.Canvas(discussions_container, yscrollcommand=scrollbar.set, bg=self.colors["background"])
        canvas.pack(side=tk.LEFT, fill="both", expand=True)
        
        scrollbar.config(command=canvas.yview)
        
        # Create frame inside canvas
        discussions_list = ttk.Frame(canvas)
        canvas.create_window((0, 0), window=discussions_list, anchor="nw")
        
        # Get all discussions
        self.db.cursor.execute('''
            SELECT d.id, b.title, d.title, d.content, u.username, d.created_at
            FROM discussions d
            JOIN books b ON d.book_id = b.id
            JOIN users u ON d.user_email = u.email
            ORDER BY d.created_at DESC
        ''')
        
        discussions = self.db.cursor.fetchall()
        
        if not discussions:
            no_discussions_label = ttk.Label(discussions_list, 
                                           text="No discussions available.",
                                           font=("Segoe UI", 12))
            no_discussions_label.pack(pady=20)
        else:
            # Display discussions
            for i, (disc_id, book_title, disc_title, content, username, created_at) in enumerate(discussions):
                disc_frame = ttk.Frame(discussions_list)
                disc_frame.pack(fill="x", padx=10, pady=10)
                
                # Discussion header
                header_frame = ttk.Frame(disc_frame)
                header_frame.pack(fill="x")
                
                title_label = ttk.Label(header_frame,
                                      text=disc_title,
                                      font=("Garamond", 14, "bold"))
                title_label.pack(side=tk.LEFT)
                
                book_label = ttk.Label(header_frame,
                                     text=f"on {book_title}",
                                     font=("Garamond", 12, "italic"))
                book_label.pack(side=tk.LEFT, padx=5)
                
                # Discussion content - show brief preview only
                content_preview = content[:150] + "..." if len(content) > 150 else content
                content_label = ttk.Label(disc_frame,
                                        text=content_preview,
                                        wraplength=600)
                content_label.pack(pady=5)
                
                # Discussion footer
                footer_frame = ttk.Frame(disc_frame)
                footer_frame.pack(fill="x")
                
                author_label = ttk.Label(footer_frame,
                                       text=f"by {username} on {created_at}",
                                       font=("Garamond", 10))
                author_label.pack(side=tk.LEFT)
                
                # View discussion button
                view_btn = tk.Button(footer_frame,
                                   text="View Discussion",
                                   command=lambda d=disc_id, b=book_title: self.view_discussion(b, d),
                                   bg=self.colors["button_primary"],
                                   fg="white",
                                   font=("Garamond", 12),
                                   relief=tk.FLAT)
                view_btn.pack(side=tk.RIGHT, padx=5)
                
                # Add separator between discussions
                ttk.Separator(discussions_list, orient="horizontal").pack(fill="x", pady=5)
        
        # Update canvas scroll region
        discussions_list.update_idletasks()
        canvas.config(scrollregion=canvas.bbox("all"))

    def setup_reader_profile_tab(self):
        # Clear existing content
        for widget in self.profile_frame.winfo_children():
            widget.destroy()
        
        # Create background canvas with gradient
        canvas = tk.Canvas(self.profile_frame, bg=self.colors["background"],
                         highlightthickness=0)
        canvas.pack(fill="both", expand=True)
        
        # Draw gradient background
        self.draw_gradient_background(canvas, 1024, 768, 
                                   self.colors["background_gradient"][0], 
                                   self.colors["background_gradient"][1])
        
        # Get user information
        self.db.cursor.execute('''
            SELECT username, full_name, email, avatar, reading_streak, books_read
            FROM users
            WHERE email = ?
        ''', (self.current_user,))
        user_info = self.db.cursor.fetchone()
        
        if not user_info:
            return
            
        username, full_name, email, avatar_data, reading_streak, books_read = user_info
        
        # Create main profile card
        profile_card = ttk.Frame(canvas, style="Card.TFrame")
        profile_width = 500
        profile_height = 600
        profile_card.place(x=(1024-profile_width)//2, y=(768-profile_height)//2,
                         width=profile_width, height=profile_height)
        
        # Apply shadow effect
        self.apply_shadow_effect(profile_card)
        
        # Header section with avatar
        header_frame = ttk.Frame(profile_card, style="Card.TFrame")
        header_frame.pack(pady=20, fill="x")
        
        # User avatar
        avatar_frame = ttk.Frame(header_frame, style="Card.TFrame")
        avatar_frame.pack(pady=10)
        
        if avatar_data:
            try:
                avatar_img = Image.open(io.BytesIO(avatar_data))
                avatar_img = avatar_img.resize((120, 120))
                avatar_photo = ImageTk.PhotoImage(avatar_img)
                avatar_label = ttk.Label(avatar_frame, image=avatar_photo, background=self.colors["card_bg"])
                avatar_label.image = avatar_photo  # Keep a reference
                avatar_label.pack()
            except Exception:
                # Fall back to placeholder avatar
                avatar_img = self.create_avatar_placeholder(120, 120, username[0].upper() if username else "U")
                avatar_photo = ImageTk.PhotoImage(avatar_img)
                avatar_label = ttk.Label(avatar_frame, image=avatar_photo, background=self.colors["card_bg"])
                avatar_label.image = avatar_photo
                avatar_label.pack()
        else:
            # Create placeholder avatar
            avatar_img = self.create_avatar_placeholder(120, 120, username[0].upper() if username else "U")
            avatar_photo = ImageTk.PhotoImage(avatar_img)
            avatar_label = ttk.Label(avatar_frame, image=avatar_photo, background=self.colors["card_bg"])
            avatar_label.image = avatar_photo
            avatar_label.pack()
        
        # Username and full name
        name_frame = ttk.Frame(header_frame, style="Card.TFrame")
        name_frame.pack(pady=10)
        
        username_label = ttk.Label(name_frame,
                                text=username,
                                font=("Garamond", 24, "bold"),
                                foreground=self.colors["primary"],
                                background=self.colors["card_bg"])
        username_label.pack()
        
        if full_name:
            fullname_label = ttk.Label(name_frame,
                     text=full_name,
                                    font=("Garamond", 16),
                                    foreground=self.colors["text"],
                                    background=self.colors["card_bg"])
            fullname_label.pack()
        
        # User stats section
        stats_frame = ttk.Frame(profile_card, style="Card.TFrame")
        stats_frame.pack(pady=15, padx=30, fill="x")
        
        # Theme toggle section
        theme_frame = ttk.Frame(profile_card, style="Card.TFrame")
        theme_frame.pack(pady=10, padx=30, fill="x")
        
        theme_label = ttk.Label(theme_frame,
                             text="Theme:",
                             font=("Garamond", 14, "bold"),
                             foreground=self.colors["primary"],
                             background=self.colors["card_bg"])
        theme_label.pack(side=tk.LEFT, pady=5)
        
        theme_btn = tk.Button(theme_frame,
                            text="Toggle Light/Dark",
                            command=self.toggle_theme,
                            bg=self.colors["button_secondary"],
                            fg="white",
                            font=("Garamond", 12),
                            relief=tk.FLAT,
                            cursor="hand2")
        theme_btn.pack(side=tk.RIGHT, padx=10, pady=5)
        
        # Buttons section
        buttons_frame = ttk.Frame(profile_card, style="Card.TFrame")
        buttons_frame.pack(pady=20, padx=30, fill="x")
        
        # Edit profile button
        edit_btn = tk.Button(buttons_frame,
                           text="Edit Profile",
                           command=self.edit_reader_profile,
                           bg=self.colors["button_primary"],
                           fg="white",
                           font=("Garamond", 12),
                           relief=tk.FLAT)
        edit_btn.pack(fill="x", pady=5)
        
        # About button
        about_btn = tk.Button(buttons_frame,
                            text="About bookverse",
                            command=self.show_about,
                            bg=self.colors["button_secondary"],
                            fg="white",
                            font=("Garamond", 12),
                            relief=tk.FLAT)
        about_btn.pack(fill="x", pady=5)
        
        # Logout button
        logout_btn = tk.Button(buttons_frame,
                             text="Logout",
                             command=self.logout,
                             bg="#FF6B6B",
                             fg="white",
                             font=("Garamond", 12),
                             relief=tk.FLAT)
        logout_btn.pack(fill="x", pady=5)

    def edit_reader_profile(self):
        # Clear existing content
        for widget in self.profile_frame.winfo_children():
            widget.destroy()
        
        # Create back button
        back_button = ttk.Button(self.profile_frame,
                               text="← Back",
                               command=self.setup_reader_profile_tab)
        back_button.pack(anchor="w", padx=10, pady=5)
        
        # Get current user information
        self.db.cursor.execute('''
            SELECT username, full_name
            FROM users
            WHERE email = ?
        ''', (self.current_user,))
        username, full_name = self.db.cursor.fetchone()
        
        # Create title
        title_label = ttk.Label(self.profile_frame,
                              text="Edit Profile",
                              font=("Segoe UI", 16, "bold"))
        title_label.pack(pady=10)
        
        # Username
        ttk.Label(self.profile_frame,
                 text="Username:",
                 font=("Segoe UI", 12)).pack(pady=5)
        self.edit_username = ttk.Entry(self.profile_frame, width=30)
        self.edit_username.insert(0, username)
        self.edit_username.pack(pady=5)
        
        # Full name
        ttk.Label(self.profile_frame,
                 text="Full Name:",
                 font=("Segoe UI", 12)).pack(pady=5)
        self.edit_full_name = ttk.Entry(self.profile_frame, width=30)
        if full_name:
            self.edit_full_name.insert(0, full_name)
        self.edit_full_name.pack(pady=5)
        
        # Save button
        save_btn = tk.Button(self.profile_frame,
                           text="Save Changes",
                           command=self.save_reader_profile,
                           bg=self.colors["button_primary"],
                           fg="white",
                           font=("Segoe UI", 11, "bold"),
                           relief=tk.FLAT)
        save_btn.pack(pady=20)

    def save_reader_profile(self):
        username = self.edit_username.get()
        full_name = self.edit_full_name.get()
        
        if not username:
            messagebox.showerror("Error", "Username cannot be empty")
            return
        
        self.db.cursor.execute('''
            UPDATE users
            SET username = ?, full_name = ?
            WHERE email = ?
        ''', (username, full_name, self.current_user))
        self.db.conn.commit()
        
        messagebox.showinfo("Success", "Profile updated successfully!")
        self.setup_reader_profile_tab()

    def logout(self):
        # Destroy the main frame
        self.main_frame.destroy()
        
        # Remove the menu bar
        self.root.config(menu="")
        
        # Create new authentication frame
        self.auth_frame = ttk.Frame(self.root)
        self.auth_frame.pack(expand=True, fill="both")
        
        # Show authentication screen
        self.show_auth_screen()

    def show_about(self):
        # Display about info in the main window instead of a popup window
        if self.user_type == "reader":
            # Clear existing content in the content_frame (browse tab)
            for widget in self.content_frame.winfo_children():
                widget.destroy()
            
            # Create back button
            back_button = ttk.Button(self.content_frame,
                                   text="← Back",
                                   command=self.setup_browse_tab)
            back_button.pack(anchor="w", padx=10, pady=5)
            
            # Title
            title_label = ttk.Label(self.content_frame,
                                  text="About bookverse Reader",
                                  font=("Segoe UI", 16, "bold"))
            title_label.pack(pady=20)
            
            # Version
            version_label = ttk.Label(self.content_frame,
                                    text="Version 1.0",
                                    font=("Segoe UI", 12))
            version_label.pack(pady=5)
            
            # Description
            desc_label = ttk.Label(self.content_frame,
                                 text="A cozy place for book lovers",
                                 font=("Segoe UI", 12, "italic"))
            desc_label.pack(pady=5)
            
            # Copyright
            copyright_label = ttk.Label(self.content_frame,
                                      text="© 2024 bookverse Reader",
                                      font=("Segoe UI", 10))
            copyright_label.pack(pady=20)
            
            # Select the browse tab to show the about content
            self.notebook.select(0)
        else:
            # For author interface, create a popup as before
            about_window = tk.Toplevel(self.root)
            about_window.title("About bookverse")
            about_window.geometry("500x400")
            about_window.configure(bg=self.colors["background"])
            
            # Title
            title_label = ttk.Label(about_window,
                                  text="About bookverse Reader",
                                  font=("Segoe UI", 16, "bold"))
            title_label.pack(pady=20)
            
            # Version
            version_label = ttk.Label(about_window,
                                    text="Version 1.0",
                                    font=("Segoe UI", 12))
            version_label.pack(pady=5)
            
            # Description
            desc_label = ttk.Label(about_window,
                                 text="A cozy place for book lovers",
                                 font=("Segoe UI", 12, "italic"))
            desc_label.pack(pady=5)
            
            # Copyright
            copyright_label = ttk.Label(about_window,
                                      text="© 2024 bookverse Reader",
                                      font=("Segoe UI", 10))
            copyright_label.pack(pady=20)
            
            # Close button
            close_btn = tk.Button(about_window,
                                text="Close",
                                command=about_window.destroy,
                                bg=self.colors["button_primary"],
                                fg="white",
                                font=("Segoe UI", 11, "bold"),
                                relief=tk.FLAT)
            close_btn.pack(pady=20)

    def show_support_form(self):
        # Clear existing content
        if self.user_type == "reader":
            parent_frame = self.profile_frame
            back_command = self.setup_reader_profile_tab
        else:
            parent_frame = self.content_frame
            back_command = self.show_author_profile
            
        # Clear parent frame
        for widget in parent_frame.winfo_children():
            widget.destroy()
        
        # Create back button
        back_button = ttk.Button(parent_frame,
                               text="← Back",
                               command=back_command)
        back_button.pack(anchor="w", padx=10, pady=5)
        
        # Title
        title_label = ttk.Label(parent_frame,
                              text="Contact Support",
                              font=("Segoe UI", 16, "bold"))
        title_label.pack(pady=20)
        
        # Create button container for different options
        button_frame = ttk.Frame(parent_frame)
        button_frame.pack(fill="x", pady=10)
        
        # New query button
        new_query_btn = tk.Button(button_frame,
                                text="New Query",
                                command=lambda: self.show_new_query_form(parent_frame),
                                bg=self.colors["button_primary"],
                                fg="white",
                                font=("Segoe UI", 11, "bold"),
                                relief=tk.FLAT)
        new_query_btn.pack(side=tk.LEFT, padx=10)
        
        # History button
        history_btn = tk.Button(button_frame,
                              text="Query History",
                              command=lambda: self.view_support_history(parent_frame),
                              bg=self.colors["button_secondary"],
                              fg="white",
                              font=("Segoe UI", 11, "bold"),
                              relief=tk.FLAT)
        history_btn.pack(side=tk.LEFT, padx=10)
        
        # Show new query form by default
        self.show_new_query_form(parent_frame)
    
    def show_new_query_form(self, parent_frame):
        # Clear existing form content
        for widget in parent_frame.winfo_children():
            if isinstance(widget, ttk.Frame) and widget != parent_frame.winfo_children()[0] and widget != parent_frame.winfo_children()[1] and widget != parent_frame.winfo_children()[2]:
                widget.destroy()
        
        # Create form container
        form_frame = ttk.Frame(parent_frame)
        form_frame.pack(fill="both", expand=True, padx=20, pady=10)
        
        # Subject
        ttk.Label(form_frame,
                 text="Subject:",
                 font=("Segoe UI", 12)).pack(pady=5)
        self.support_subject = ttk.Entry(form_frame, width=40)
        self.support_subject.pack(pady=5)
        
        # Content
        ttk.Label(form_frame,
                 text="Description:",
                 font=("Segoe UI", 12)).pack(pady=5)
        self.support_content = tk.Text(form_frame, width=40, height=10)
        self.support_content.pack(pady=5)
        
        # Submit button
        submit_btn = tk.Button(form_frame,
                             text="Submit",
                             command=self.submit_support_query,
                             bg=self.colors["button_primary"],
                             fg="white",
                             font=("Segoe UI", 11, "bold"),
                             relief=tk.FLAT)
        submit_btn.pack(pady=20)
    
    def view_support_history(self, parent_frame):
        # Clear existing content, keep the header and buttons
        for widget in parent_frame.winfo_children():
            if isinstance(widget, ttk.Frame) and widget != parent_frame.winfo_children()[0] and widget != parent_frame.winfo_children()[1] and widget != parent_frame.winfo_children()[2]:
                widget.destroy()
        
        # Create container for history
        history_frame = ttk.Frame(parent_frame)
        history_frame.pack(fill="both", expand=True, padx=20, pady=10)
        
        # Add scrollbar
        scrollbar = ttk.Scrollbar(history_frame)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        # Create canvas for queries
        canvas = tk.Canvas(history_frame, yscrollcommand=scrollbar.set, bg=self.colors["background"])
        canvas.pack(side=tk.LEFT, fill="both", expand=True)
        
        scrollbar.config(command=canvas.yview)
        
        # Create frame inside canvas
        queries_frame = ttk.Frame(canvas)
        canvas.create_window((0, 0), window=queries_frame, anchor="nw")
        
        # Get user email for query - handle dictionary or string format
        user_email = self.current_user
        if isinstance(self.current_user, dict):
            user_email = self.current_user["email"]
        
        # Get user's support queries
        self.db.cursor.execute('''
            SELECT sq.id, sq.subject, sq.content, sq.status, sq.created_at
            FROM support_queries sq
            WHERE sq.user_email = ?
            ORDER BY sq.created_at DESC
        ''', (user_email,))
        
        queries = self.db.cursor.fetchall()
        
        if not queries:
            no_queries_label = ttk.Label(queries_frame, 
                                       text="You haven't submitted any support queries yet.",
                                       font=("Segoe UI", 12))
            no_queries_label.pack(pady=20)
        else:
            # Display each query with responses
            for query_id, subject, content, status, created_at in queries:
                query_frame = ttk.Frame(queries_frame)
                query_frame.pack(fill="x", padx=10, pady=10)
                
                # Query header with status
                header_frame = ttk.Frame(query_frame)
                header_frame.pack(fill="x")
                
                subject_label = ttk.Label(header_frame,
                                        text=subject,
                                        font=("Garamond", 14, "bold"))
                subject_label.pack(side=tk.LEFT)
                
                status_color = "#5cb85c" if status == "Resolved" else "#f0ad4e"
                status_label = ttk.Label(header_frame,
                                       text=f"Status: {status}",
                                       font=("Garamond", 12),
                                       foreground=status_color)
                status_label.pack(side=tk.RIGHT)
                
                # Date
                date_label = ttk.Label(query_frame,
                                     text=f"Submitted on: {created_at}",
                                     font=("Garamond", 10, "italic"))
                date_label.pack(anchor="w", pady=(5, 0))
                
                # Query content
                content_label = ttk.Label(query_frame,
                                        text=content,
                                        wraplength=700)
                content_label.pack(pady=5, anchor="w")
                
                # Add separator
                ttk.Separator(query_frame, orient="horizontal").pack(fill="x", pady=5)
                
                # Debug query ID
                print(f"Checking responses for query ID: {query_id}")
                
                # Get responses for this query
                try:
                    self.db.cursor.execute('''
                        SELECT sr.content, u.username, sr.created_at
                        FROM support_responses sr
                        LEFT JOIN users u ON sr.tech_support_email = u.email
                        WHERE sr.query_id = ?
                        ORDER BY sr.created_at
                    ''', (query_id,))
                    
                    responses = self.db.cursor.fetchall()
                    print(f"Found {len(responses)} responses")
                    
                    if responses:
                        # Response section
                        response_section = ttk.Frame(query_frame)
                        response_section.pack(fill="x", pady=5)
                        
                        ttk.Label(response_section,
                                text="Responses:",
                                font=("Garamond", 12, "bold")).pack(anchor="w")
                        
                        # Display each response
                        for response_content, tech_username, response_date in responses:
                            tech_name = tech_username if tech_username else "Tech Support"
                            response_frame = ttk.Frame(response_section)
                            response_frame.pack(fill="x", pady=5)
                            
                            # Response meta
                            ttk.Label(response_frame,
                                    text=f"From: {tech_name} on {response_date}",
                                    font=("Garamond", 10, "italic")).pack(anchor="w")
                            
                            # Response content
                            ttk.Label(response_frame,
                                    text=response_content,
                                    wraplength=650).pack(padx=15, pady=5, anchor="w")
                    else:
                        # No responses yet
                        ttk.Label(query_frame,
                                text="No responses yet. Our team will get back to you soon.",
                                font=("Garamond", 11, "italic")).pack(pady=5)
                        
                except Exception as e:
                    print(f"Error getting responses: {str(e)}")
                    ttk.Label(query_frame,
                            text=f"Error loading responses: {str(e)}",
                            font=("Garamond", 11, "italic")).pack(pady=5)
                
                # Final separator
                ttk.Separator(queries_frame, orient="horizontal").pack(fill="x", pady=10)
        
        # Update canvas scroll region
        queries_frame.update_idletasks()
        canvas.config(scrollregion=canvas.bbox("all"))

    def submit_support_query(self):
        subject = self.support_subject.get()
        content = self.support_content.get("1.0", tk.END).strip()
        
        if not subject or not content:
            messagebox.showerror("Error", "Please fill in all fields")
            return
        
        self.db.cursor.execute('''
            INSERT INTO support_queries (user_email, subject, content)
            VALUES (?, ?, ?)
        ''', (self.current_user, subject, content))
        self.db.conn.commit()
        
        messagebox.showinfo("Success", "Support query submitted successfully!")
        self.support_subject.delete(0, tk.END)
        self.support_content.delete("1.0", tk.END)

    def show_author_interface(self):
        # Clear existing content
        for widget in self.main_frame.winfo_children():
            widget.destroy()
        
        # Create navigation frame
        nav_frame = ttk.Frame(self.main_frame)
        nav_frame.pack(fill="x", padx=10, pady=5)
        
        # Create navigation buttons
        my_books_btn = ttk.Button(nav_frame, text="My Books", command=self.show_my_books)
        my_books_btn.pack(side=tk.LEFT, padx=5)
        
        upload_btn = ttk.Button(nav_frame, text="Upload Book", command=self.show_upload_form)
        upload_btn.pack(side=tk.LEFT, padx=5)
        
        discussions_btn = ttk.Button(nav_frame, text="Discussions", command=self.show_author_discussions)
        discussions_btn.pack(side=tk.LEFT, padx=5)
        
        profile_btn = ttk.Button(nav_frame, text="Profile", command=self.show_author_profile)
        profile_btn.pack(side=tk.LEFT, padx=5)
        
        # Replace Support button with My Reviews button
        reviews_btn = ttk.Button(nav_frame, text="My Reviews", command=self.show_author_reviews)
        reviews_btn.pack(side=tk.LEFT, padx=5)
        
        # Create content frame
        self.content_frame = ttk.Frame(self.main_frame)
        self.content_frame.pack(fill="both", expand=True, padx=10, pady=10)
        
        # Show my books by default
        self.show_my_books()
    
    def show_author_reviews(self):
        """Display all reviews for the books published by the current author"""
        # Clear content frame
        for widget in self.content_frame.winfo_children():
            widget.destroy()
        
        # Create title
        title_label = ttk.Label(self.content_frame, text="Reviews for My Books", font=("Segoe UI", 16, "bold"))
        title_label.pack(pady=10)
        
        # Get all books published by this author
        self.db.cursor.execute('''
            SELECT id, title
            FROM books
            WHERE author_email = ?
            ORDER BY title
        ''', (self.current_user,))
        
        books = self.db.cursor.fetchall()
        
        if not books:
            # No books published yet
            no_books_label = ttk.Label(self.content_frame, 
                                     text="You haven't published any books yet.",
                                     font=("Segoe UI", 12))
            no_books_label.pack(pady=20)
            return
        
        # Create a scrollable frame for reviews
        reviews_container = ttk.Frame(self.content_frame)
        reviews_container.pack(fill="both", expand=True, padx=10, pady=10)
        
        # Add scrollbar
        scrollbar = ttk.Scrollbar(reviews_container)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        # Create canvas for reviews
        canvas = tk.Canvas(reviews_container, yscrollcommand=scrollbar.set)
        canvas.pack(side=tk.LEFT, fill="both", expand=True)
        
        scrollbar.config(command=canvas.yview)
        
        # Create frame inside canvas
        reviews_frame = ttk.Frame(canvas)
        canvas.create_window((0, 0), window=reviews_frame, anchor="nw")
        
        # Add reviews for each book
        has_reviews = False
        
        for book_id, book_title in books:
            # Get reviews for this book
            self.db.cursor.execute('''
                SELECT r.rating, r.comment, u.username, r.review_date
                FROM reviews r
                JOIN users u ON r.user_email = u.email
                WHERE r.book_id = ?
                ORDER BY r.review_date DESC
            ''', (book_id,))
            
            book_reviews = self.db.cursor.fetchall()
            
            if book_reviews:
                has_reviews = True
                
                # Book header
                book_header = ttk.Frame(reviews_frame)
                book_header.pack(fill="x", padx=10, pady=5)
                
                book_title_label = ttk.Label(book_header,
                                           text=f"Reviews for: {book_title}",
                                           font=("Segoe UI", 14, "bold"))
                book_title_label.pack(anchor="w")
                
                ttk.Separator(reviews_frame, orient="horizontal").pack(fill="x", padx=10, pady=5)
                
                # Display reviews for this book
                for rating, comment, username, review_date in book_reviews:
                    review_frame = ttk.Frame(reviews_frame)
                    review_frame.pack(fill="x", padx=20, pady=10)
                    
                    # Rating (stars)
                    rating_label = ttk.Label(review_frame,
                                           text="★" * rating + "☆" * (5-rating),
                                           font=("Segoe UI", 12),
                                           foreground="#FFD700")  # Gold color for stars
                    rating_label.pack(anchor="w")
                    
                    # Comment
                    comment_label = ttk.Label(review_frame,
                                            text=comment,
                                            wraplength=700)
                    comment_label.pack(pady=5, anchor="w")
                    
                    # Reviewer info
                    info_label = ttk.Label(review_frame,
                                         text=f"by {username} on {review_date}",
                                         font=("Segoe UI", 10))
                    info_label.pack(anchor="w")
                    
                    # Add separator between reviews
                    ttk.Separator(reviews_frame, orient="horizontal").pack(fill="x", padx=20, pady=5)
        
        if not has_reviews:
            no_reviews_label = ttk.Label(reviews_frame, 
                                       text="Your books don't have any reviews yet.",
                                       font=("Segoe UI", 12))
            no_reviews_label.pack(pady=20)
        
        # Update canvas scroll region
        reviews_frame.update_idletasks()
        canvas.config(scrollregion=canvas.bbox("all"))

    def show_my_books(self):
        # Clear content frame
        for widget in self.content_frame.winfo_children():
            widget.destroy()
        
        # Create title
        title_label = ttk.Label(self.content_frame, text="My Books", font=("Segoe UI", 16, "bold"))
        title_label.pack(pady=10)
        
        # Display author's books
        self.display_author_books()

    def show_upload_form(self):
        # Clear content frame
        for widget in self.content_frame.winfo_children():
            widget.destroy()
        
        # Create title
        title_label = ttk.Label(self.content_frame, text="Upload New Book", font=("Segoe UI", 16, "bold"))
        title_label.pack(pady=10)
        
        # Create upload form
        self.setup_upload_tab()

    def show_author_discussions(self):
        # Clear content frame
        for widget in self.content_frame.winfo_children():
            widget.destroy()
        
        # Create title
        title_label = ttk.Label(self.content_frame, text="Book Discussions", font=("Segoe UI", 16, "bold"))
        title_label.pack(pady=10)
        
        # Display discussions
        self.display_author_discussions()

    def show_author_profile(self):
        # Clear existing content
        for widget in self.content_frame.winfo_children():
            widget.destroy()
        
        # Create title
        title_label = ttk.Label(self.content_frame, text="My Profile", font=("Segoe UI", 16, "bold"))
        title_label.pack(pady=10)
        
        # Display profile
        self.setup_profile_tab()

    def display_author_books(self):
        # Clear existing books
        for widget in self.content_frame.winfo_children():
            widget.destroy()
        
        # Get author's books
        self.db.cursor.execute('''
            SELECT id, title, description, upload_date, amazon_link
            FROM books
            WHERE author_email = ?
            ORDER BY upload_date DESC
        ''', (self.current_user,))
        
        books = self.db.cursor.fetchall()
        
        # Display books in a grid
        for i, (book_id, title, description, upload_date, amazon_link) in enumerate(books):
            book_frame = ttk.Frame(self.content_frame)
            book_frame.pack(fill="x", padx=10, pady=10)
            
            # Book title
            title_label = ttk.Label(book_frame,
                                  text=title,
                                  font=("Segoe UI", 14, "bold"))
            title_label.pack(pady=5)
            
            # Upload date
            date_label = ttk.Label(book_frame,
                                 text=f"Uploaded: {upload_date}",
                                 font=("Segoe UI", 10))
            date_label.pack(pady=5)
            
            # Description
            desc_label = ttk.Label(book_frame,
                                 text=description,
                                 wraplength=300)
            desc_label.pack(pady=5)
            
            # Buttons frame
            btn_frame = ttk.Frame(book_frame)
            btn_frame.pack(pady=10)
            
            # View/Read button
            view_btn = tk.Button(btn_frame,
                               text="View/Read",
                               command=lambda t=title: self.view_book(t),
                               bg=self.colors["button_primary"],
                               fg="white",
                               font=("Segoe UI", 11, "bold"),
                               relief=tk.FLAT)
            view_btn.pack(side=tk.LEFT, padx=5)
            
            # Buy on Amazon button (if link available)
            if amazon_link:
                amazon_btn = tk.Button(btn_frame,
                                     text="Buy on Amazon",
                                     command=lambda l=amazon_link: self.open_amazon_link(l),
                                     bg="#FF9900",  # Amazon orange
                                     fg="white",
                                     font=("Segoe UI", 11, "bold"),
                                     relief=tk.FLAT)
                amazon_btn.pack(side=tk.LEFT, padx=5)
            
            # Discussion button
            discussion_btn = tk.Button(btn_frame,
                                     text="Discussions",
                                     command=lambda t=title: self.view_book_discussions(t),
                                     bg=self.colors["button_secondary"],
                                     fg="white",
                                     font=("Segoe UI", 11, "bold"),
                                     relief=tk.FLAT)
            discussion_btn.pack(side=tk.LEFT, padx=5)
            
            # Edit and Delete buttons (for author)
            edit_btn = tk.Button(btn_frame,
                               text="Edit",
                               command=lambda b=book_id: self.edit_book(b),
                               bg=self.colors["button_primary"],
                               fg="white",
                               font=("Segoe UI", 11, "bold"),
                               relief=tk.FLAT)
            edit_btn.pack(side=tk.LEFT, padx=5)
            
            delete_btn = tk.Button(btn_frame,
                                 text="Delete",
                                 command=lambda b=book_id, t=title: self.delete_book(b, t),
                                 bg="#FF4444",  # Red color for delete
                                 fg="white",
                                 font=("Segoe UI", 11, "bold"),
                                 relief=tk.FLAT)
            delete_btn.pack(side=tk.LEFT, padx=5)
            
            # Add separator between books
            ttk.Separator(self.content_frame, orient="horizontal").pack(fill="x", padx=10, pady=5)

    def edit_book(self, book_id):
        # Clear existing content
        for widget in self.content_frame.winfo_children():
            widget.destroy()
        
        # Create back button
        back_button = ttk.Button(self.content_frame,
                               text="← Back",
                               command=self.show_my_books)
        back_button.pack(anchor="w", padx=10, pady=5)
        
        # Get book information
        self.db.cursor.execute('''
            SELECT title, description, amazon_link
            FROM books
            WHERE id = ?
        ''', (book_id,))
        title, description, amazon_link = self.db.cursor.fetchone()
        
        # Create title
        title_label = ttk.Label(self.content_frame,
                              text="Edit Book",
                              font=("Segoe UI", 16, "bold"))
        title_label.pack(pady=10)
        
        # Title
        ttk.Label(self.content_frame,
                 text="Title:",
                 font=("Segoe UI", 12)).pack(pady=5)
        self.edit_book_title = ttk.Entry(self.content_frame, width=40)
        self.edit_book_title.insert(0, title)
        self.edit_book_title.pack(pady=5)
        
        # Description
        ttk.Label(self.content_frame,
                 text="Description:",
                 font=("Segoe UI", 12)).pack(pady=5)
        self.edit_book_description = tk.Text(self.content_frame, width=40, height=5)
        self.edit_book_description.insert("1.0", description)
        self.edit_book_description.pack(pady=5)
        
        # Amazon link
        ttk.Label(self.content_frame,
                 text="Amazon Link:",
                 font=("Segoe UI", 12)).pack(pady=5)
        
        # Create a frame to hold the Amazon link components
        amazon_frame = ttk.Frame(self.content_frame)
        amazon_frame.pack(pady=5, fill="x", padx=20)
        
        # Use Text widget instead of Entry for better paste support
        self.edit_book_amazon = tk.Text(amazon_frame, width=40, height=1)
        if amazon_link:
            self.edit_book_amazon.insert("1.0", amazon_link)
        self.edit_book_amazon.pack(side=tk.LEFT, fill="x", expand=True)
        
        # Add a paste button for convenience
        paste_btn = ttk.Button(amazon_frame, text="Paste", 
                            command=lambda: self.paste_from_clipboard_to_field(self.edit_book_amazon))
        paste_btn.pack(side=tk.LEFT, padx=5)
        
        # Save button
        save_btn = tk.Button(self.content_frame,
                           text="Save Changes",
                           command=lambda: self.save_book_edit(book_id),
                           bg=self.colors["button_primary"],
                           fg="white",
                           font=("Segoe UI", 11, "bold"),
                           relief=tk.FLAT)
        save_btn.pack(pady=20)

    def paste_from_clipboard_to_field(self, text_widget):
        """Safely paste clipboard content to a text widget"""
        try:
            clipboard_content = self.root.clipboard_get()
            text_widget.delete("1.0", tk.END)
            text_widget.insert("1.0", clipboard_content)
        except Exception as e:
            self.show_toast("Clipboard is empty or contains non-text content", "warning")

    def save_book_edit(self, book_id):
        title = self.edit_book_title.get()
        description = self.edit_book_description.get("1.0", tk.END).strip()
        amazon_link = self.edit_book_amazon.get("1.0", tk.END).strip()
        
        if not title or not description:
            messagebox.showerror("Error", "Title and description cannot be empty")
            return
        
        self.db.cursor.execute('''
            UPDATE books
            SET title = ?, description = ?, amazon_link = ?
            WHERE id = ?
        ''', (title, description, amazon_link, book_id))
        self.db.conn.commit()
        
        messagebox.showinfo("Success", "Book updated successfully!")
        self.display_author_books()

    def delete_book(self, book_id, title):
        if messagebox.askyesno("Confirm Delete", f"Are you sure you want to delete '{title}'?"):
            self.db.cursor.execute('DELETE FROM books WHERE id = ?', (book_id,))
            self.db.conn.commit()
            self.display_author_books()
            messagebox.showinfo("Success", f"Book '{title}' deleted successfully")

    def setup_upload_tab(self):
        # Create upload tab
        upload_frame = ttk.Frame(self.content_frame)
        upload_frame.pack(pady=20)
        
        # Upload form
        form_frame = ttk.Frame(upload_frame)
        form_frame.pack(pady=20)
        
        # Title
        ttk.Label(form_frame,
                 text="Title:",
                 font=("Garamond", 12)).pack(pady=5)
        self.upload_title = ttk.Entry(form_frame, width=40)
        self.upload_title.pack(pady=5)
        
        # Description
        ttk.Label(form_frame,
                 text="Description:",
                 font=("Garamond", 12)).pack(pady=5)
        self.upload_description = tk.Text(form_frame, width=40, height=5)
        self.upload_description.pack(pady=5)
        
        # Amazon link
        ttk.Label(form_frame,
                 text="Amazon Link (optional):",
                 font=("Garamond", 12)).pack(pady=5)
        
        # Create a frame for Amazon link and paste button
        amazon_frame = ttk.Frame(form_frame)
        amazon_frame.pack(pady=5)
        
        self.upload_amazon = ttk.Entry(amazon_frame, width=35)
        self.upload_amazon.pack(side=tk.LEFT, padx=5)
        
        # Add paste button for Amazon link
        paste_btn = tk.Button(amazon_frame,
                            text="Paste",
                            command=lambda: self.paste_from_clipboard_to_entry(self.upload_amazon),
                            bg=self.colors["button_secondary"],
                            fg="white",
                            font=("Garamond", 10),
                            relief=tk.FLAT)
        paste_btn.pack(side=tk.LEFT, padx=5)
        
        # PDF URL
        ttk.Label(form_frame,
                 text="PDF URL:",
                 font=("Garamond", 12)).pack(pady=5)
        self.upload_pdf_path = tk.StringVar()
        pdf_frame = ttk.Frame(form_frame)
        pdf_frame.pack(pady=5)
        ttk.Entry(pdf_frame, textvariable=self.upload_pdf_path, width=30).pack(side=tk.LEFT, padx=5)
        browse_btn = tk.Button(pdf_frame,
                             text="Browse",
                             command=self.browse_pdf,
                             bg=self.colors["button_primary"],
                             fg="white",
                             font=("Garamond", 12),
                             relief=tk.FLAT)
        browse_btn.pack(side=tk.LEFT, padx=5)
        
        # Upload button
        upload_btn = tk.Button(form_frame,
                             text="Upload Book",
                             command=self.upload_book,
                             bg=self.colors["button_primary"],
                             fg="white",
                             font=("Garamond", 12),
                             relief=tk.FLAT)
        upload_btn.pack(pady=20)

    def browse_pdf(self):
        file_path = filedialog.askopenfilename(
            filetypes=[("PDF files", "*.pdf")]
        )
        if file_path:
            self.upload_pdf_path.set(file_path)

    def upload_book(self):
        title = self.upload_title.get()
        description = self.upload_description.get("1.0", tk.END).strip()
        amazon_link = self.upload_amazon.get()
        pdf_path = self.upload_pdf_path.get()
        
        if not all([title, description, pdf_path]):
            messagebox.showerror("Error", "Please fill in all required fields")
            return
        
        try:
            # Read PDF file as binary data
            with open(pdf_path, 'rb') as pdf_file:
                pdf_data = pdf_file.read()
            
            # Use None for empty Amazon link so it's stored as NULL in the database
            if not amazon_link:
                amazon_link = None
            
            # Add book to database with PDF data
            self.db.cursor.execute('''
                INSERT INTO books (title, author_email, description, pdf_data, amazon_link)
                VALUES (?, ?, ?, ?, ?)
            ''', (title, self.current_user, description, pdf_data, amazon_link))
            self.db.conn.commit()
            
            # Clear form
            self.upload_title.delete(0, tk.END)
            self.upload_description.delete("1.0", tk.END)
            self.upload_amazon.delete(0, tk.END)
            self.upload_pdf_path.set("")
            
            messagebox.showinfo("Success", "Book uploaded successfully!")
            self.display_author_books()
            
        except Exception as e:
            messagebox.showerror("Error", f"Failed to upload book: {str(e)}")

    def display_author_discussions(self):
        # Clear existing discussions
        for widget in self.content_frame.winfo_children():
            widget.destroy()
        
        # Get discussions on author's books
        self.db.cursor.execute('''
            SELECT d.id, b.title, d.title, d.content, u.username, d.created_at, b.author_email
            FROM discussions d
            JOIN users u ON d.user_email = u.email
            JOIN books b ON d.book_id = b.id
            WHERE b.author_email = ?
            ORDER BY d.created_at DESC
        ''', (self.current_user,))
        
        discussions = self.db.cursor.fetchall()
        
        # Display discussions
        for i, (disc_id, book_title, disc_title, content, username, created_at, author_email) in enumerate(discussions):
            disc_frame = ttk.Frame(self.content_frame)
            disc_frame.pack(fill="x", padx=10, pady=10)
            
            # Discussion header
            header_frame = ttk.Frame(disc_frame)
            header_frame.pack(fill="x")
            
            title_label = ttk.Label(header_frame,
                                  text=disc_title,
                                  font=("Garamond", 14, "bold"))
            title_label.pack(side=tk.LEFT)
            
            book_label = ttk.Label(header_frame,
                                 text=f"on {book_title}",
                                 font=("Garamond", 12, "italic"))
            book_label.pack(side=tk.LEFT, padx=5)
            
            # Discussion content
            content_label = ttk.Label(disc_frame,
                                    text=content,
                                    wraplength=600)
            content_label.pack(pady=5)
            
            # Discussion footer
            footer_frame = ttk.Frame(disc_frame)
            footer_frame.pack(fill="x")
            
            # Create author badge only if the user is both the book's author and the discussion poster
            author_info = f"by {username}"
            if self.current_user == author_email:
                author_info += " 👑"  # Author badge
            
            info_label = ttk.Label(footer_frame,
                                 text=f"{author_info} on {created_at}",
                                 font=("Garamond", 10))
            info_label.pack(side=tk.LEFT)
            
            # View discussion button
            view_btn = tk.Button(footer_frame,
                               text="View Discussion",
                               command=lambda d=disc_id: self.view_discussion_popup(book_title, d),
                               bg=self.colors["button_primary"],
                               fg="white",
                               font=("Garamond", 12),
                               relief=tk.FLAT)
            view_btn.pack(side=tk.RIGHT, padx=5)

    def setup_profile_tab(self):
        # Create profile tab
        profile_frame = ttk.Frame(self.content_frame)
        profile_frame.pack(pady=20)
        
        # Get user information
        self.db.cursor.execute('''
            SELECT username, full_name
            FROM users
            WHERE email = ?
        ''', (self.current_user,))
        username, full_name = self.db.cursor.fetchone()
        
        # Profile information
        info_frame = ttk.Frame(profile_frame)
        info_frame.pack(pady=20)
        
        ttk.Label(info_frame,
                 text="Username:",
                 font=("Garamond", 12, "bold")).pack()
        ttk.Label(info_frame,
                 text=username,
                 font=("Garamond", 12)).pack(pady=5)
        
        ttk.Label(info_frame,
                 text="Email:",
                 font=("Garamond", 12, "bold")).pack()
        ttk.Label(info_frame,
                 text=self.current_user,
                 font=("Garamond", 12)).pack(pady=5)
        
        if full_name:
            ttk.Label(info_frame,
                     text="Full Name:",
                     font=("Garamond", 12, "bold")).pack()
            ttk.Label(info_frame,
                     text=full_name,
                     font=("Garamond", 12)).pack(pady=5)
        
        # Edit profile button
        edit_btn = tk.Button(profile_frame,
                           text="Edit Profile",
                           command=self.edit_author_profile,
                           bg=self.colors["button_primary"],
                           fg="white",
                           font=("Garamond", 12),
                           relief=tk.FLAT)
        edit_btn.pack(pady=10)
        
        # Toggle theme button
        theme_icon = "☀" if self.dark_mode else "☽"
        theme_text = f"Toggle Theme ({theme_icon})"
        theme_btn = tk.Button(profile_frame,
                            text=theme_text,
                            command=self.toggle_theme,
                            bg=self.colors["button_secondary"],
                            fg="white",
                            font=("Garamond", 12),
                            relief=tk.FLAT)
        theme_btn.pack(pady=10)
        
        # Footer buttons
        footer_frame = ttk.Frame(profile_frame)
        footer_frame.pack(pady=20)
        
        # About button
        about_btn = tk.Button(footer_frame,
                            text="About",
                            command=self.show_about,
                            bg=self.colors["button_secondary"],
                            fg="white",
                            font=("Garamond", 12),
                            relief=tk.FLAT)
        about_btn.pack(side=tk.LEFT, padx=10)
        
        # Support button
        support_btn = tk.Button(footer_frame,
                              text="Contact Support",
                              command=self.show_support_form,
                              bg=self.colors["button_secondary"],
                              fg="white",
                              font=("Garamond", 12),
                              relief=tk.FLAT)
        support_btn.pack(side=tk.LEFT, padx=10)
        
        # Logout button
        logout_btn = tk.Button(footer_frame,
                             text="Logout",
                             command=self.logout,
                             bg=self.colors["button_primary"],
                             fg="white",
                             font=("Garamond", 12),
                             relief=tk.FLAT)
        logout_btn.pack(side=tk.LEFT, padx=10)

    def edit_author_profile(self):
        # Clear existing content
        for widget in self.content_frame.winfo_children():
            widget.destroy()
        
        # Create back button
        back_button = ttk.Button(self.content_frame,
                               text="← Back",
                               command=self.show_author_profile)
        back_button.pack(anchor="w", padx=10, pady=5)
        
        # Get current user information
        self.db.cursor.execute('''
            SELECT username, full_name, date_of_birth, gender, book_genre_preference
            FROM users
            WHERE email = ?
        ''', (self.current_user,))
        username, full_name, date_of_birth, gender, genre_preference = self.db.cursor.fetchone()
        
        # Create title
        title_label = ttk.Label(self.content_frame,
                              text="Edit Profile",
                              font=("Segoe UI", 16, "bold"))
        title_label.pack(pady=10)
        
        # Username
        ttk.Label(self.content_frame,
                 text="Username:",
                 font=("Segoe UI", 12)).pack(pady=5)
        self.edit_username = ttk.Entry(self.content_frame, width=30)
        self.edit_username.insert(0, username)
        self.edit_username.pack(pady=5)
        
        # Full name
        ttk.Label(self.content_frame,
                 text="Full Name:",
                 font=("Segoe UI", 12)).pack(pady=5)
        self.edit_full_name = ttk.Entry(self.content_frame, width=30)
        if full_name:
            self.edit_full_name.insert(0, full_name)
        self.edit_full_name.pack(pady=5)
        
        # Date of Birth
        ttk.Label(self.content_frame,
                 text="Date of Birth (YYYY-MM-DD):",
                 font=("Segoe UI", 12)).pack(pady=5)
        self.edit_dob = ttk.Entry(self.content_frame, width=30)
        if date_of_birth:
            self.edit_dob.insert(0, date_of_birth)
        self.edit_dob.pack(pady=5)
        
        # Gender
        ttk.Label(self.content_frame,
                 text="Gender:",
                 font=("Segoe UI", 12)).pack(pady=5)
        self.edit_gender = ttk.Combobox(self.content_frame, 
                                      values=["Male", "Female", "Other"],
                                      width=27)
        if gender:
            self.edit_gender.set(gender)
        self.edit_gender.pack(pady=5)
        
        # Book Genre Preference
        ttk.Label(self.content_frame,
                 text="Favorite Genre:",
                 font=("Segoe UI", 12)).pack(pady=5)
        self.edit_genre = ttk.Combobox(self.content_frame,
                                     values=["Fiction", "Non-Fiction", "Mystery", "Science Fiction",
                                            "Fantasy", "Romance", "Biography", "History", "Self-Help"],
                                     width=27)
        if genre_preference:
            self.edit_genre.set(genre_preference)
        self.edit_genre.pack(pady=5)
        
        # Save button
        save_btn = tk.Button(self.content_frame,
                           text="Save Changes",
                           command=self.save_author_profile,
                           bg=self.colors["button_primary"],
                           fg="white",
                           font=("Segoe UI", 11, "bold"),
                           relief=tk.FLAT)
        save_btn.pack(pady=20)

    def save_author_profile(self):
        username = self.edit_username.get()
        full_name = self.edit_full_name.get()
        date_of_birth = self.edit_dob.get()
        gender = self.edit_gender.get()
        genre_preference = self.edit_genre.get()
        
        if not username:
            messagebox.showerror("Error", "Username cannot be empty")
            return
            
        try:
            # Validate date format if provided
            if date_of_birth:
                datetime.strptime(date_of_birth, "%Y-%m-%d")
            
            self.db.cursor.execute('''
                UPDATE users
                SET username = ?, full_name = ?, date_of_birth = ?, 
                    gender = ?, book_genre_preference = ?
                WHERE email = ?
            ''', (username, full_name, date_of_birth, gender, genre_preference, self.current_user))
            self.db.conn.commit()
            
            messagebox.showinfo("Success", "Profile updated successfully!")
            self.show_author_profile()
            
        except ValueError:
            messagebox.showerror("Error", "Invalid date format. Please use YYYY-MM-DD")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to update profile: {str(e)}")

    def view_book_discussions(self, book_title):
        # Clear existing content
        for widget in self.content_frame.winfo_children():
            widget.destroy()
        
        # Create back button
        back_button = ttk.Button(self.content_frame,
                               text="← Back",
                               command=self.setup_browse_tab)
        back_button.pack(anchor="w", padx=10, pady=5)
        
        # Create title 
        title_label = ttk.Label(self.content_frame, 
                              text=f"Discussions: {book_title}",
                              font=("Segoe UI", 16, "bold"))
        title_label.pack(pady=10)
        
        # Get book discussions
        self.db.cursor.execute('''
            SELECT d.id, d.title, d.content, u.username, d.created_at, b.author_email, d.user_email
            FROM discussions d
            JOIN users u ON d.user_email = u.email
            JOIN books b ON d.book_id = b.id
            WHERE b.title = ?
            ORDER BY d.created_at DESC
        ''', (book_title,))
        
        discussions = self.db.cursor.fetchall()
        
        # Create discussion list with scrollbar
        discussion_container = ttk.Frame(self.content_frame)
        discussion_container.pack(fill="both", expand=True, padx=10, pady=10)
        
        # Add scrollbar
        scrollbar = ttk.Scrollbar(discussion_container)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        # Create canvas for discussions
        canvas = tk.Canvas(discussion_container, yscrollcommand=scrollbar.set, bg=self.colors["background"])
        canvas.pack(side=tk.LEFT, fill="both", expand=True)
        
        scrollbar.config(command=canvas.yview)
        
        # Create frame inside canvas
        discussions_frame = ttk.Frame(canvas)
        canvas.create_window((0, 0), window=discussions_frame, anchor="nw")
        
        if not discussions:
            no_discussions = ttk.Label(discussions_frame,
                                     text="No discussions available for this book yet.",
                                     font=("Segoe UI", 12))
            no_discussions.pack(pady=20)
        else:
            # Display discussions
            for i, (disc_id, title, content, username, created_at, author_email, discussion_user_email) in enumerate(discussions):
                disc_frame = ttk.Frame(discussions_frame)
                disc_frame.pack(fill="x", padx=10, pady=10)
                
                # Discussion header
                header_frame = ttk.Frame(disc_frame)
                header_frame.pack(fill="x")
                
                title_label = ttk.Label(header_frame,
                                      text=title,
                                      font=("Garamond", 14, "bold"))
                title_label.pack(side=tk.LEFT)
                
                # Discussion content - show a preview
                content_preview = content[:150] + "..." if len(content) > 150 else content
                content_label = ttk.Label(disc_frame,
                                        text=content_preview,
                                        wraplength=700)
                content_label.pack(pady=5)
                
                # Discussion footer
                footer_frame = ttk.Frame(disc_frame)
                footer_frame.pack(fill="x")
                
                # Create author badge only if the user is the book's author
                author_info = f"by {username}"
                if author_email == discussion_user_email:
                    author_info += " 👑"  # Author badge
                
                info_label = ttk.Label(footer_frame,
                                     text=f"{author_info} on {created_at}",
                                     font=("Garamond", 10))
                info_label.pack(side=tk.LEFT)
                
                # View discussion button
                view_btn = tk.Button(footer_frame,
                                   text="View Discussion",
                                   command=lambda d=disc_id, b=book_title: self.view_discussion(b, d),
                                   bg=self.colors["button_primary"],
                                   fg="white",
                                   font=("Garamond", 12),
                                   relief=tk.FLAT)
                view_btn.pack(side=tk.RIGHT, padx=5)
                
                # Add separator between discussions
                ttk.Separator(discussions_frame, orient="horizontal").pack(fill="x", pady=5)
        
        # Update canvas scroll region
        discussions_frame.update_idletasks()
        canvas.config(scrollregion=canvas.bbox("all"))
        
        # Add new discussion button
        new_discussion_btn = tk.Button(self.content_frame,
                                     text="Start New Discussion",
                                     command=lambda: self.start_new_discussion(book_title),
                                     bg=self.colors["button_primary"],
                                     fg="white",
                                     font=("Garamond", 12),
                                     relief=tk.FLAT)
        new_discussion_btn.pack(pady=10)


    def view_discussion(self, book_title, discussion_id):
        # Store the current notebook tab
        current_tab_index = self.notebook.index(self.notebook.select())
        is_discussions_tab = (current_tab_index == 2)  # Check if we're on the Discussions tab (index 2)
        
        # Determine which frame to use for display
        target_frame = self.discussions_frame if is_discussions_tab else self.content_frame
        
        # Clear existing content
        for widget in target_frame.winfo_children():
            widget.destroy()
        
        # Create back button with appropriate callback
        back_command = self.setup_reader_discussions_tab if is_discussions_tab else lambda: self.view_book_discussions(book_title)
        back_button = ttk.Button(target_frame,
                               text="← Back",
                               command=back_command)
        back_button.pack(anchor="w", padx=10, pady=5)
        
        # Get discussion details
        self.db.cursor.execute('''
            SELECT d.title, d.content, u.username, d.created_at, b.author_email, d.user_email
            FROM discussions d
            JOIN users u ON d.user_email = u.email
            JOIN books b ON d.book_id = b.id
            WHERE d.id = ?
        ''', (discussion_id,))
        
        discussion = self.db.cursor.fetchone()
        
        if not discussion:
            ttk.Label(target_frame, text="Discussion not found!").pack(pady=20)
            return
            
        disc_title, content, username, created_at, author_email, user_email = discussion
        
        # Create title
        title_label = ttk.Label(target_frame,
                              text=disc_title,
                              font=("Segoe UI", 16, "bold"),
                              wraplength=750)
        title_label.pack(pady=(0, 10))
        
        # Book title
        book_label = ttk.Label(target_frame,
                             text=f"Book: {book_title}",
                             font=("Segoe UI", 12, "italic"))
        book_label.pack(pady=(0, 5))
        
        # Author info with badge if appropriate
        author_info = f"Posted by {username}"
        if author_email == user_email:
            author_info += " 👑"  # Author badge
            
        author_label = ttk.Label(target_frame,
                               text=f"{author_info} on {created_at}",
                               font=("Segoe UI", 10))
        author_label.pack(pady=(0, 15))
        
        # Separator
        ttk.Separator(target_frame, orient="horizontal").pack(fill="x", pady=5)
        
        # Discussion content
        content_frame = ttk.Frame(target_frame)
        content_frame.pack(fill="both", expand=True, pady=10)
        
        # Create scrollable text for content
        content_scrollbar = ttk.Scrollbar(content_frame)
        content_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        content_text = tk.Text(content_frame, 
                             wrap=tk.WORD,
                             height=10,
                             font=("Segoe UI", 12),
                             yscrollcommand=content_scrollbar.set,
                             bg=self.colors["background"],
                             relief=tk.FLAT)
        content_text.pack(fill="both", expand=True)
        content_text.insert(tk.END, content)
        content_text.config(state="disabled")  # Make read-only
        
        content_scrollbar.config(command=content_text.yview)
        
        # Get comments/replies
        self.db.cursor.execute('''
            SELECT r.content, u.username, r.created_at, b.author_email, r.user_email
            FROM discussion_replies r
            JOIN users u ON r.user_email = u.email
            JOIN discussions d ON r.discussion_id = d.id
            JOIN books b ON d.book_id = b.id
            WHERE r.discussion_id = ?
            ORDER BY r.created_at ASC
        ''', (discussion_id,))
        
        replies = self.db.cursor.fetchall()
        
        # Comments/replies section
        replies_label = ttk.Label(target_frame, 
                                text=f"Replies ({len(replies)})",
                                font=("Segoe UI", 14, "bold"))
        replies_label.pack(pady=(15, 5), anchor="w")
        
        # Create scrollable container for replies
        replies_container = ttk.Frame(target_frame)
        replies_container.pack(fill="both", expand=True, pady=5)
        
        replies_scrollbar = ttk.Scrollbar(replies_container)
        replies_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        replies_canvas = tk.Canvas(replies_container, 
                                 yscrollcommand=replies_scrollbar.set,
                                 bg=self.colors["background"],
                                 highlightthickness=0)
        replies_canvas.pack(side=tk.LEFT, fill="both", expand=True)
        
        replies_scrollbar.config(command=replies_canvas.yview)
        
        replies_frame = ttk.Frame(replies_canvas)
        replies_canvas.create_window((0, 0), window=replies_frame, anchor="nw")
        
        if not replies:
            no_replies = ttk.Label(replies_frame, 
                                 text="No replies yet. Be the first to reply!",
                                 font=("Segoe UI", 12, "italic"))
            no_replies.pack(pady=10)
        else:
            for reply_content, reply_username, reply_date, author_email, reply_user_email in replies:
                reply_frame = ttk.Frame(replies_frame)
                reply_frame.pack(fill="x", pady=5)
                
                # Reply author info with badge if appropriate
                reply_author = f"{reply_username}"
                if author_email == reply_user_email:
                    reply_author += " 👑"  # Author badge
                    
                reply_header = ttk.Label(reply_frame,
                                       text=f"{reply_author} on {reply_date}:",
                                       font=("Segoe UI", 10, "bold"))
                reply_header.pack(anchor="w")
                
                reply_text = ttk.Label(reply_frame,
                                     text=reply_content,
                                     wraplength=700,
                                     font=("Segoe UI", 11))
                reply_text.pack(anchor="w", padx=10, pady=5)
                
                # Add separator between replies
                ttk.Separator(replies_frame, orient="horizontal").pack(fill="x", pady=2)
        
        # Update scrollregion
        replies_frame.update_idletasks()
        replies_canvas.config(scrollregion=replies_canvas.bbox("all"))
        
        # Add reply form
        reply_label = ttk.Label(target_frame, 
                              text="Add a Reply:",
                              font=("Segoe UI", 12, "bold"))
        reply_label.pack(pady=(15, 5), anchor="w")
        
        self.reply_content = tk.Text(target_frame, height=4, width=80)
        self.reply_content.pack(pady=5, fill="x", padx=10)
        
        reply_btn = tk.Button(target_frame,
                            text="Submit Reply",
                            command=lambda: self.submit_reply(discussion_id),
                            bg=self.colors["button_primary"],
                            fg="white",
                            font=("Segoe UI", 11, "bold"),
                            relief=tk.FLAT)
        reply_btn.pack(pady=10, anchor="e", padx=10)
        
    def submit_reply(self, discussion_id):
        content = self.reply_content.get("1.0", tk.END).strip()
        
        if not content:
            messagebox.showerror("Error", "Please enter a reply")
            return
        
        # Add reply to database
        self.db.cursor.execute('''
            INSERT INTO discussion_replies (discussion_id, user_email, content)
            VALUES (?, ?, ?)
        ''', (discussion_id, self.current_user, content))
        self.db.conn.commit()
        
        messagebox.showinfo("Success", "Reply submitted successfully!")
        self.reply_content.delete("1.0", tk.END)
        
        # Refresh the discussion view
        if hasattr(self, 'current_book_title') and self.current_book_title:
            # Use view_discussion instead of view_discussion_popup to respect the current tab
            self.view_discussion(self.current_book_title, discussion_id)
        else:
            # Retrieve book title from discussion id
            self.db.cursor.execute('''
                SELECT b.title 
                FROM discussions d
                JOIN books b ON d.book_id = b.id
                WHERE d.id = ?
            ''', (discussion_id,))
            result = self.db.cursor.fetchone()
            if result:
                book_title = result[0]
                # Use view_discussion instead of view_discussion_popup
                self.view_discussion(book_title, discussion_id)
        
    def start_new_discussion(self, book_title):
        # Clear existing content
        for widget in self.content_frame.winfo_children():
            widget.destroy()
        
        # Create back button
        back_button = ttk.Button(self.content_frame,
                              text="← Back",
                              command=lambda: self.view_book_discussions(book_title))
        back_button.pack(anchor="w", padx=10, pady=5)
        
        # Create title
        title_label = ttk.Label(self.content_frame,
                              text=f"New Discussion: {book_title}",
                              font=("Segoe UI", 16, "bold"))
        title_label.pack(pady=10)
        
        # Title
        ttk.Label(self.content_frame,
                text="Discussion Title:",
                font=("Segoe UI", 12)).pack(pady=5)
        self.new_discussion_title = ttk.Entry(self.content_frame, width=50)
        self.new_discussion_title.pack(pady=5)
        
        # Content
        ttk.Label(self.content_frame,
                text="Discussion Content:",
                font=("Segoe UI", 12)).pack(pady=5)
        self.new_discussion_content = tk.Text(self.content_frame, width=50, height=10)
        self.new_discussion_content.pack(pady=5)
        
        # Submit button
        submit_btn = tk.Button(self.content_frame,
                             text="Submit Discussion",
                             command=lambda: self.submit_new_discussion(book_title),
                             bg=self.colors["button_primary"],
                             fg="white",
                             font=("Segoe UI", 11, "bold"),
                             relief=tk.FLAT)
        submit_btn.pack(pady=20)
        
    def submit_new_discussion(self, book_title):
        title = self.new_discussion_title.get()
        content = self.new_discussion_content.get("1.0", tk.END).strip()
        
        if not title or not content:
            messagebox.showerror("Error", "Please fill in all fields")
            return
        
        # Get book ID
        self.db.cursor.execute('SELECT id FROM books WHERE title = ?', (book_title,))
        book_id = self.db.cursor.fetchone()[0]
        
        # Add discussion
        self.db.cursor.execute('''
            INSERT INTO discussions (book_id, user_email, title, content)
            VALUES (?, ?, ?, ?)
        ''', (book_id, self.current_user, title, content))
        self.db.conn.commit()
        
        messagebox.showinfo("Success", "Discussion created successfully!")
        
        # Clear form
        self.new_discussion_title.delete(0, tk.END)
        self.new_discussion_content.delete("1.0", tk.END)
        
        # Return to book discussions view
        self.view_book_discussions(book_title)

    def view_discussion_popup(self, book_title, discussion_id, parent_window=None):
        """Display a single discussion in the main window instead of a popup"""
        # Clear existing content in the content frame
        for widget in self.content_frame.winfo_children():
            widget.destroy()
        
        # Create back button
        back_button = ttk.Button(self.content_frame,
                               text="← Back to Discussions",
                               command=lambda: self.view_book_discussions(book_title))
        back_button.pack(anchor="w", padx=10, pady=5)
        
        # Get discussion details
        self.db.cursor.execute('''
            SELECT d.title, d.content, u.username, d.created_at, d.book_id, d.user_email
            FROM discussions d
            JOIN users u ON d.user_email = u.email
            WHERE d.id = ?
        ''', (discussion_id,))
        
        discussion = self.db.cursor.fetchone()
        
        if not discussion:
            ttk.Label(self.content_frame, text="Discussion not found!").pack(pady=20)
            return
            
        disc_title, content, username, created_at, book_id, user_email = discussion
        
        # Create container for discussion content
        main_frame = ttk.Frame(self.content_frame)
        main_frame.pack(fill="both", expand=True, padx=20, pady=20)
        
        # Discussion title
        title_label = ttk.Label(main_frame, 
                              text=disc_title,
                              font=("Garamond", 16, "bold"),
                              wraplength=650)
        title_label.pack(pady=(0, 10))
        
        # Book title
        book_label = ttk.Label(main_frame,
                             text=f"Book: {book_title}",
                             font=("Garamond", 12, "italic"))
        book_label.pack(pady=(0, 5))
        
        # Author and date
        author_label = ttk.Label(main_frame,
                               text=f"Posted by {username} on {created_at}",
                               font=("Garamond", 10))
        author_label.pack(pady=(0, 15))
        
        # Separator
        ttk.Separator(main_frame, orient="horizontal").pack(fill="x", pady=5)
        
        # Discussion content
        content_frame = ttk.Frame(main_frame)
        content_frame.pack(fill="both", expand=True, pady=10)
        
        # Add scrollbar for content
        content_scrollbar = ttk.Scrollbar(content_frame)
        content_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        content_text = tk.Text(content_frame, 
                             wrap=tk.WORD,
                             height=10,
                             font=("Garamond", 12),
                             yscrollcommand=content_scrollbar.set,
                             bg=self.colors["background"],
                             relief=tk.FLAT)
        content_text.pack(fill="both", expand=True)
        content_text.insert(tk.END, content)
        content_text.config(state="disabled")  # Make read-only
        
        content_scrollbar.config(command=content_text.yview)
        
        # Get comments for this discussion
        self.db.cursor.execute('''
            SELECT r.content, u.username, r.created_at
            FROM discussion_replies r
            JOIN users u ON r.user_email = u.email
            WHERE r.discussion_id = ?
            ORDER BY r.created_at
        ''', (discussion_id,))
        
        comments = self.db.cursor.fetchall()
        
        # Comments section
        comments_label = ttk.Label(main_frame, 
                                 text=f"Comments ({len(comments)})",
                                 font=("Garamond", 14, "bold"))
        comments_label.pack(pady=(15, 5), anchor="w")
        
        # Comments container with scrollbar
        comments_frame = ttk.Frame(main_frame)
        comments_frame.pack(fill="both", expand=True, pady=5)
        
        comments_scrollbar = ttk.Scrollbar(comments_frame)
        comments_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        comments_canvas = tk.Canvas(comments_frame, 
                                  yscrollcommand=comments_scrollbar.set,
                                  bg=self.colors["background"],
                                  highlightthickness=0)
        comments_canvas.pack(side=tk.LEFT, fill="both", expand=True)
        
        comments_scrollbar.config(command=comments_canvas.yview)
        
        comments_container = ttk.Frame(comments_canvas)
        comments_canvas.create_window((0, 0), window=comments_container, anchor="nw")
        
        if not comments:
            no_comments = ttk.Label(comments_container, 
                                  text="No comments yet. Be the first to comment!",
                                  font=("Garamond", 12, "italic"))
            no_comments.pack(pady=10)
        else:
            for comment_content, comment_user, comment_date in comments:
                comment_frame = ttk.Frame(comments_container)
                comment_frame.pack(fill="x", pady=5)
                
                comment_header = ttk.Label(comment_frame,
                                         text=f"{comment_user} on {comment_date}:",
                                         font=("Garamond", 10, "bold"))
                comment_header.pack(anchor="w")
                
                comment_text = ttk.Label(comment_frame,
                                       text=comment_content,
                                       wraplength=600,
                                       font=("Garamond", 11))
                comment_text.pack(anchor="w", padx=10, pady=5)
                
                # Add separator between comments
                ttk.Separator(comments_container, orient="horizontal").pack(fill="x", pady=2)
        
        # Update scrollregion after the comment container has been populated
        comments_container.update_idletasks()
        comments_canvas.config(scrollregion=comments_canvas.bbox("all"))
        
        # Add comment section
        add_comment_frame = ttk.Frame(main_frame)
        add_comment_frame.pack(fill="x", pady=10)
        
        comment_entry = tk.Text(add_comment_frame, height=3, width=50, font=("Garamond", 11))
        comment_entry.pack(side=tk.LEFT, fill="x", expand=True, padx=(0, 10))
        
        self.current_discussion_id = discussion_id
        self.current_book_title = book_title
        
        def add_comment():
            new_comment = comment_entry.get("1.0", tk.END).strip()
            if new_comment:
                try:
                    # Insert comment into database
                    self.db.cursor.execute('''
                        INSERT INTO discussion_replies (discussion_id, user_email, content, created_at)
                        VALUES (?, ?, ?, datetime('now', 'localtime'))
                        ''', (discussion_id, self.current_user, new_comment))
                    self.db.conn.commit()
                
                    # Refresh the discussion view to show the new comment
                    self.view_discussion_popup(book_title, discussion_id)
                except Exception as e:
                    self.show_toast(f"Error adding comment: {str(e)}", "error")
                
        comment_btn = tk.Button(add_comment_frame,
                              text="Add Comment",
                              command=add_comment,
                              bg=self.colors["button_primary"],
                              fg="white",
                              font=("Garamond", 12),
                              relief=tk.FLAT)
        comment_btn.pack(side=tk.RIGHT)
        
    def start_new_discussion_popup(self, book_title, parent_window=None):
        # Create a popup window for new discussion
        if parent_window:
            parent_window.destroy()
            
        new_discussion_window = tk.Toplevel(self.root)
        new_discussion_window.title(f"New Discussion: {book_title}")
        new_discussion_window.geometry("600x500")
        new_discussion_window.configure(bg=self.colors["background"])
        
        # Create back button
        back_button = ttk.Button(new_discussion_window,
                               text="Back to Discussions",
                               command=lambda: self.view_book_discussions(book_title))
        back_button.pack(anchor="w", padx=10, pady=5)
        
        # Title
        ttk.Label(new_discussion_window,
                 text="Discussion Title:",
                 font=("Segoe UI", 12)).pack(pady=5)
        self.new_discussion_title = ttk.Entry(new_discussion_window, width=50)
        self.new_discussion_title.pack(pady=5)
        
        # Content
        ttk.Label(new_discussion_window,
                 text="Discussion Content:",
                 font=("Segoe UI", 12)).pack(pady=5)
        self.new_discussion_content = tk.Text(new_discussion_window, width=50, height=10)
        self.new_discussion_content.pack(pady=5)
        
        # Submit button
        submit_btn = tk.Button(new_discussion_window,
                             text="Submit Discussion",
                             command=lambda: self.submit_new_discussion_popup(book_title, new_discussion_window),
                             bg=self.colors["button_primary"],
                             fg="white",
                             font=("Segoe UI", 11, "bold"),
                             relief=tk.FLAT)
        submit_btn.pack(pady=20)
        
    def submit_new_discussion_popup(self, book_title, new_discussion_window):
        title = self.new_discussion_title.get()
        content = self.new_discussion_content.get("1.0", tk.END).strip()
        
        if not title or not content:
            messagebox.showerror("Error", "Please fill in all fields")
            return
        
        # Get book ID
        self.db.cursor.execute('SELECT id FROM books WHERE title = ?', (book_title,))
        book_id = self.db.cursor.fetchone()[0]
        
        # Add discussion
        self.db.cursor.execute('''
            INSERT INTO discussions (book_id, user_email, title, content)
            VALUES (?, ?, ?, ?)
        ''', (book_id, self.current_user, title, content))
        self.db.conn.commit()
        
        messagebox.showinfo("Success", "Discussion created successfully!")
        
        # Return to book discussions view
        new_discussion_window.destroy()
        self.view_book_discussions(book_title)

    def view_reviews(self, book_title):
        # Create a popup window for reviews instead of replacing browse content
        review_window = tk.Toplevel(self.root)
        review_window.title(f"Reviews: {book_title}")
        review_window.geometry("800x600")
        review_window.configure(bg=self.colors["background"])
        
        # Create back button
        back_button = ttk.Button(review_window,
                               text="Close",
                               command=review_window.destroy)
        back_button.pack(anchor="w", padx=10, pady=5)
        
        # Get book reviews
        self.db.cursor.execute('''
            SELECT r.rating, r.comment, u.username, r.review_date
            FROM reviews r
            JOIN users u ON r.user_email = u.email
            JOIN books b ON r.book_id = b.id
            WHERE b.title = ?
            ORDER BY r.review_date DESC
        ''', (book_title,))
        
        reviews = self.db.cursor.fetchall()
        
        # Create reviews list
        reviews_list = ttk.Frame(review_window)
        reviews_list.pack(fill="both", expand=True, padx=10, pady=10)
        
        # Add scrollbar
        scrollbar = ttk.Scrollbar(reviews_list)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        # Create canvas for reviews
        canvas = tk.Canvas(reviews_list, yscrollcommand=scrollbar.set, bg=self.colors["background"])
        canvas.pack(side=tk.LEFT, fill="both", expand=True)
        
        scrollbar.config(command=canvas.yview)
        
        # Create frame inside canvas
        reviews_frame = ttk.Frame(canvas)
        canvas.create_window((0, 0), window=reviews_frame, anchor="nw")
        
        # Display reviews
        for rating, comment, username, review_date in reviews:
            review_frame = ttk.Frame(reviews_frame)
            review_frame.pack(fill="x", padx=10, pady=10)
            
            # Rating (stars)
            rating_label = ttk.Label(review_frame,
                                   text="★" * rating + "☆" * (5-rating),
                                   font=("Segoe UI", 12),
                                   foreground="#FFD700")  # Gold color for stars
            rating_label.pack(anchor="w")
            
            # Comment
            comment_label = ttk.Label(review_frame,
                                    text=comment,
                                    wraplength=700)
            comment_label.pack(pady=5)
            
            # Reviewer info
            info_label = ttk.Label(review_frame,
                                 text=f"by {username} on {review_date}",
                                 font=("Segoe UI", 10))
            info_label.pack(anchor="w")
            
            # Add separator between reviews
            ttk.Separator(reviews_frame, orient="horizontal").pack(fill="x", pady=5)
        
        # Update canvas scroll region
        reviews_frame.update_idletasks()
        canvas.config(scrollregion=canvas.bbox("all"))
        
        # Add review form
        review_form = ttk.Frame(review_window)
        review_form.pack(fill="x", padx=10, pady=10)
        
        ttk.Label(review_form,
                 text="Write a Review:",
                 font=("Segoe UI", 12)).pack(pady=5)
        
        # Rating selection
        rating_frame = ttk.Frame(review_form)
        rating_frame.pack(pady=5)
        ttk.Label(rating_frame, text="Rating:").pack(side=tk.LEFT)
        self.review_rating = tk.IntVar()
        for i in range(1, 6):
            ttk.Radiobutton(rating_frame, text=str(i), variable=self.review_rating, value=i).pack(side=tk.LEFT, padx=5)
        
        # Review comment
        self.review_comment = tk.Text(review_form, width=70, height=5)
        self.review_comment.pack(pady=5)
        
        # Submit button
        submit_btn = tk.Button(review_form,
                             text="Submit Review",
                             command=lambda: self.submit_review_popup(book_title, review_window),
                             bg=self.colors["button_primary"],
                             fg="white",
                             font=("Segoe UI", 11, "bold"),
                             relief=tk.FLAT)
        submit_btn.pack(pady=10)

    def submit_review_popup(self, book_title, review_window):
        rating = self.review_rating.get()
        comment = self.review_comment.get("1.0", tk.END).strip()
        
        if not rating:
            messagebox.showerror("Error", "Please select a rating")
            return
            
        if not comment:
            messagebox.showerror("Error", "Please write a review comment")
            return
        
        try:
            # Get book ID
            self.db.cursor.execute('SELECT id FROM books WHERE title = ?', (book_title,))
            book_id = self.db.cursor.fetchone()[0]
            
            # Add review to database
            self.db.cursor.execute('''
                INSERT INTO reviews (book_id, user_email, rating, comment)
                VALUES (?, ?, ?, ?)
            ''', (book_id, self.current_user, rating, comment))
            self.db.conn.commit()
            
            messagebox.showinfo("Success", "Review submitted successfully!")
            self.review_comment.delete("1.0", tk.END)
            self.review_rating.set(0)
            
            # Refresh the reviews in the same popup
            review_window.destroy()
            self.view_reviews(book_title)
            
        except Exception as e:
            messagebox.showerror("Error", f"Failed to submit review: {str(e)}")

    def show_tech_support_interface(self):
        """Display tech support interface for handling support queries"""
        # Clear existing content
        for widget in self.main_frame.winfo_children():
            widget.destroy()
        
        # Create top menu frame
        menu_frame = ttk.Frame(self.main_frame)
        menu_frame.pack(fill="x", pady=10)
        
        # Create section buttons
        support_btn = tk.Button(menu_frame,
                              text="Support Queries",
                              command=lambda: self.show_tech_support_section("support"),
                              bg=self.colors["button_primary"],
                              fg="white",
                              font=("Garamond", 12),
                              relief=tk.FLAT)
        support_btn.pack(side=tk.LEFT, padx=5)
        
        moderate_books_btn = tk.Button(menu_frame,
                                     text="Moderate Books",
                                     command=lambda: self.show_tech_support_section("books"),
                                     bg=self.colors["button_secondary"],
                                     fg="white",
                                     font=("Garamond", 12),
                                     relief=tk.FLAT)
        moderate_books_btn.pack(side=tk.LEFT, padx=5)
        
        moderate_reviews_btn = tk.Button(menu_frame,
                                      text="Moderate Reviews",
                                      command=lambda: self.show_tech_support_section("reviews"),
                                      bg=self.colors["button_secondary"],
                                      fg="white",
                                      font=("Garamond", 12),
                                      relief=tk.FLAT)
        moderate_reviews_btn.pack(side=tk.LEFT, padx=5)
        
        moderate_discussions_btn = tk.Button(menu_frame,
                                         text="Moderate Discussions",
                                         command=lambda: self.show_tech_support_section("discussions"),
                                         bg=self.colors["button_secondary"],
                                         fg="white",
                                         font=("Garamond", 12),
                                         relief=tk.FLAT)
        moderate_discussions_btn.pack(side=tk.LEFT, padx=5)
        
        settings_btn = tk.Button(menu_frame,
                               text="Settings",
                               command=lambda: self.show_tech_support_section("settings"),
                               bg=self.colors["button_secondary"],
                               fg="white",
                               font=("Garamond", 12),
                               relief=tk.FLAT)
        settings_btn.pack(side=tk.LEFT, padx=5)
        
        # Store section buttons for reference
        self.tech_section_buttons = {
            "support": support_btn,
            "books": moderate_books_btn,
            "reviews": moderate_reviews_btn,
            "discussions": moderate_discussions_btn,
            "settings": settings_btn
        }
        
        # Create container for content
        self.tech_content_frame = ttk.Frame(self.main_frame)
        self.tech_content_frame.pack(fill="both", expand=True, padx=10, pady=10)
        
        # Show support section by default
        self.show_tech_support_section("support")
        
        # We've removed the logout button at the bottom since it's now in the Settings tab
    
    def show_tech_support_section(self, section):
        """Show the selected section in the tech support interface"""
        # Update button styling
        for section_name, button in self.tech_section_buttons.items():
            if section_name == section:
                button.config(bg=self.colors["button_primary"])
            else:
                button.config(bg=self.colors["button_secondary"])
        
        # Clear content frame
        for widget in self.tech_content_frame.winfo_children():
            widget.destroy()
            
        # Section-specific title
        section_titles = {
            "support": "Support Queries",
            "books": "Moderate Books",
            "reviews": "Moderate Reviews",
            "discussions": "Moderate Discussions",
            "settings": "Settings"
        }
        
        title_label = ttk.Label(self.tech_content_frame, 
                              text=section_titles[section],
                              font=("Segoe UI", 16, "bold"))
        title_label.pack(pady=10)
        
        # Show appropriate section content
        if section == "support":
            self.show_support_queries_section()
        elif section == "books":
            self.show_books_moderation_section()
        elif section == "reviews":
            self.show_reviews_moderation_section()
        elif section == "discussions":
            self.show_discussions_moderation_section()
        elif section == "settings":
            self.show_tech_settings_section()
    
    def show_support_queries_section(self):
        """Show the support queries section with active/resolved toggle"""
        # Create toggle frame for view selection
        toggle_frame = ttk.Frame(self.tech_content_frame)
        toggle_frame.pack(fill="x", pady=10)
        
        # Create active queries button (highlighted by default)
        self.active_btn = tk.Button(toggle_frame,
                                  text="Active Queries",
                                  command=lambda: self.toggle_tech_support_view("active"),
                                  bg=self.colors["button_primary"],
                                  fg="white",
                                  font=("Garamond", 12),
                                  relief=tk.FLAT)
        self.active_btn.pack(side=tk.LEFT, padx=10)
        
        # Create resolved queries button
        self.resolved_btn = tk.Button(toggle_frame,
                                    text="Resolved Queries",
                                    command=lambda: self.toggle_tech_support_view("resolved"),
                                    bg=self.colors["button_secondary"],
                                    fg="white",
                                    font=("Garamond", 12),
                                    relief=tk.FLAT)
        self.resolved_btn.pack(side=tk.LEFT, padx=10)
        
        # Create container frame for queries
        self.queries_container = ttk.Frame(self.tech_content_frame)
        self.queries_container.pack(fill="both", expand=True, padx=10, pady=10)
        
        # Show active queries by default
        self.current_view = "active"
        self.load_tech_support_queries()
    
    def show_books_moderation_section(self):
        """Show the books moderation section"""
        # Create container for books
        books_container = ttk.Frame(self.tech_content_frame)
        books_container.pack(fill="both", expand=True, padx=10, pady=10)
        
        # Add scrollbar
        scrollbar = ttk.Scrollbar(books_container)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        # Create canvas for books
        canvas = tk.Canvas(books_container, yscrollcommand=scrollbar.set, bg=self.colors["background"])
        canvas.pack(side=tk.LEFT, fill="both", expand=True)
        
        scrollbar.config(command=canvas.yview)
        
        # Create frame inside canvas
        books_frame = ttk.Frame(canvas)
        canvas.create_window((0, 0), window=books_frame, anchor="nw")
        
        # Get all books
        self.db.cursor.execute('''
            SELECT b.id, b.title, b.description, u.username, u.email
            FROM books b
            JOIN users u ON b.author_email = u.email
            ORDER BY b.title
        ''')
        
        books = self.db.cursor.fetchall()
        
        if not books:
            no_books_label = ttk.Label(books_frame, 
                                      text="No books available.",
                                      font=("Segoe UI", 12))
            no_books_label.pack(pady=20)
        else:
            # Display books in a list
            for book_id, title, description, author, author_email in books:
                book_frame = ttk.Frame(books_frame)
                book_frame.pack(fill="x", padx=10, pady=10)
                
                # Book title
                title_label = ttk.Label(book_frame,
                                      text=title,
                                      font=("Garamond", 14, "bold"))
                title_label.pack(anchor="w")
                
                # Author
                author_label = ttk.Label(book_frame,
                                       text=f"by {author} ({author_email})",
                                       font=("Garamond", 12, "italic"))
                author_label.pack(anchor="w")
                
                # Description preview
                desc_preview = description[:150] + "..." if len(description) > 150 else description
                desc_label = ttk.Label(book_frame,
                                     text=desc_preview,
                                     wraplength=700)
                desc_label.pack(pady=5, anchor="w")
                
                # Button frame
                button_frame = ttk.Frame(book_frame)
                button_frame.pack(fill="x", pady=5)
                
                # Delete button
                delete_btn = tk.Button(button_frame,
                                     text="Remove Book",
                                     command=lambda b_id=book_id, b_title=title: self.tech_delete_book(b_id, b_title),
                                     bg="#d9534f",  # Bootstrap's danger red
                                     fg="white",
                                     font=("Garamond", 12),
                                     relief=tk.FLAT)
                delete_btn.pack(side=tk.RIGHT, padx=5)
                
                # Add separator between books
                ttk.Separator(books_frame, orient="horizontal").pack(fill="x", pady=5)
                
        # Update canvas scroll region
        books_frame.update_idletasks()
        canvas.config(scrollregion=canvas.bbox("all"))
    
    def show_reviews_moderation_section(self):
        """Show the reviews moderation section"""
        # Create container for reviews
        reviews_container = ttk.Frame(self.tech_content_frame)
        reviews_container.pack(fill="both", expand=True, padx=10, pady=10)
        
        # Add scrollbar
        scrollbar = ttk.Scrollbar(reviews_container)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        # Create canvas for reviews
        canvas = tk.Canvas(reviews_container, yscrollcommand=scrollbar.set, bg=self.colors["background"])
        canvas.pack(side=tk.LEFT, fill="both", expand=True)
        
        scrollbar.config(command=canvas.yview)
        
        # Create frame inside canvas
        reviews_frame = ttk.Frame(canvas)
        canvas.create_window((0, 0), window=reviews_frame, anchor="nw")
        
        # Get all reviews
        self.db.cursor.execute('''
            SELECT r.id, b.title, r.rating, r.comment, u.username, u.email, r.review_date
            FROM reviews r
            JOIN books b ON r.book_id = b.id
            JOIN users u ON r.user_email = u.email
            ORDER BY r.review_date DESC
        ''')
        
        reviews = self.db.cursor.fetchall()
        
        if not reviews:
            no_reviews_label = ttk.Label(reviews_frame, 
                                      text="No reviews available.",
                                      font=("Segoe UI", 12))
            no_reviews_label.pack(pady=20)
        else:
            # Display reviews
            for review_id, book_title, rating, comment, username, email, review_date in reviews:
                review_frame = ttk.Frame(reviews_frame)
                review_frame.pack(fill="x", padx=10, pady=10)
                
                # Header with book title
                header_frame = ttk.Frame(review_frame)
                header_frame.pack(fill="x")
                
                title_label = ttk.Label(header_frame,
                                      text=f"Review for: {book_title}",
                                      font=("Garamond", 14, "bold"))
                title_label.pack(side=tk.LEFT)
                
                # Rating (stars)
                rating_label = ttk.Label(header_frame,
                                       text="★" * rating + "☆" * (5-rating),
                                       font=("Garamond", 14),
                                       foreground="#FFD700")  # Gold color for stars
                rating_label.pack(side=tk.RIGHT)
                
                # User info
                user_label = ttk.Label(review_frame,
                                     text=f"by {username} ({email}) on {review_date}",
                                     font=("Garamond", 10, "italic"))
                user_label.pack(anchor="w")
                
                # Review content
                content_label = ttk.Label(review_frame,
                                        text=comment,
                                        wraplength=700)
                content_label.pack(pady=5, anchor="w")
                
                # Button frame
                button_frame = ttk.Frame(review_frame)
                button_frame.pack(fill="x", pady=5)
                
                # Delete button
                delete_btn = tk.Button(button_frame,
                                     text="Remove Review",
                                     command=lambda r_id=review_id: self.tech_delete_review(r_id),
                                     bg="#d9534f",  # Bootstrap's danger red
                                     fg="white",
                                     font=("Garamond", 12),
                                     relief=tk.FLAT)
                delete_btn.pack(side=tk.RIGHT, padx=5)
                
                # Add separator between reviews
                ttk.Separator(reviews_frame, orient="horizontal").pack(fill="x", pady=5)
        
        # Update canvas scroll region
        reviews_frame.update_idletasks()
        canvas.config(scrollregion=canvas.bbox("all"))
    
    def show_discussions_moderation_section(self):
        """Show the discussions moderation section"""
        # Create container for discussions
        discussions_container = ttk.Frame(self.tech_content_frame)
        discussions_container.pack(fill="both", expand=True, padx=10, pady=10)
        
        # Add scrollbar
        scrollbar = ttk.Scrollbar(discussions_container)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        # Create canvas for discussions
        canvas = tk.Canvas(discussions_container, yscrollcommand=scrollbar.set, bg=self.colors["background"])
        canvas.pack(side=tk.LEFT, fill="both", expand=True)
        
        scrollbar.config(command=canvas.yview)
        
        # Create frame inside canvas
        discussions_frame = ttk.Frame(canvas)
        canvas.create_window((0, 0), window=discussions_frame, anchor="nw")
        
        # Get all discussions
        self.db.cursor.execute('''
            SELECT d.id, b.title, d.title, d.content, u.username, u.email, d.created_at
            FROM discussions d
            JOIN books b ON d.book_id = b.id
            JOIN users u ON d.user_email = u.email
            ORDER BY d.created_at DESC
        ''')
        
        discussions = self.db.cursor.fetchall()
        
        if not discussions:
            no_discussions_label = ttk.Label(discussions_frame, 
                                          text="No discussions available.",
                                          font=("Segoe UI", 12))
            no_discussions_label.pack(pady=20)
        else:
            # Display discussions
            for disc_id, book_title, disc_title, content, username, email, created_at in discussions:
                disc_frame = ttk.Frame(discussions_frame)
                disc_frame.pack(fill="x", padx=10, pady=10)
                
                # Discussion header
                header_frame = ttk.Frame(disc_frame)
                header_frame.pack(fill="x")
                
                title_label = ttk.Label(header_frame,
                                      text=disc_title,
                                      font=("Garamond", 14, "bold"))
                title_label.pack(side=tk.LEFT)
                
                book_label = ttk.Label(header_frame,
                                     text=f"on {book_title}",
                                     font=("Garamond", 12, "italic"))
                book_label.pack(side=tk.LEFT, padx=5)
                
                # User info
                user_label = ttk.Label(disc_frame,
                                     text=f"by {username} ({email}) on {created_at}",
                                     font=("Garamond", 10, "italic"))
                user_label.pack(anchor="w")
                
                # Discussion content - show preview
                content_preview = content[:200] + "..." if len(content) > 200 else content
                content_label = ttk.Label(disc_frame,
                                        text=content_preview,
                                        wraplength=700)
                content_label.pack(pady=5, anchor="w")
                
                # Get number of replies
                self.db.cursor.execute('''
                    SELECT COUNT(*) FROM discussion_replies WHERE discussion_id = ?
                ''', (disc_id,))
                
                reply_count = self.db.cursor.fetchone()[0]
                replies_label = ttk.Label(disc_frame,
                                        text=f"{reply_count} replies",
                                        font=("Garamond", 10))
                replies_label.pack(anchor="w")
                
                # Button frame
                button_frame = ttk.Frame(disc_frame)
                button_frame.pack(fill="x", pady=5)
                
                # View discussion button
                view_btn = tk.Button(button_frame,
                                   text="View Full Discussion",
                                   command=lambda d_id=disc_id, b_title=book_title: self.view_discussion(b_title, d_id),
                                   bg=self.colors["button_secondary"],
                                   fg="white",
                                   font=("Garamond", 12),
                                   relief=tk.FLAT)
                view_btn.pack(side=tk.LEFT, padx=5)
                
                # Delete button
                delete_btn = tk.Button(button_frame,
                                     text="Remove Discussion",
                                     command=lambda d_id=disc_id: self.tech_delete_discussion(d_id),
                                     bg="#d9534f",  # Bootstrap's danger red
                                     fg="white",
                                     font=("Garamond", 12),
                                     relief=tk.FLAT)
                delete_btn.pack(side=tk.RIGHT, padx=5)
                
                # Add separator between discussions
                ttk.Separator(discussions_frame, orient="horizontal").pack(fill="x", pady=5)
        
        # Update canvas scroll region
        discussions_frame.update_idletasks()
        canvas.config(scrollregion=canvas.bbox("all"))
    
    def tech_delete_book(self, book_id, title):
        """Delete a book as tech support"""
        if not messagebox.askyesno("Confirm Deletion", f"Are you sure you want to delete the book '{title}'?\nThis will also delete all associated reviews and discussions."):
            return
            
        try:
            # Delete associated discussions and replies
            self.db.cursor.execute('''
                SELECT id FROM discussions WHERE book_id = ?
            ''', (book_id,))
            
            discussion_ids = self.db.cursor.fetchall()
            
            for (disc_id,) in discussion_ids:
                # Delete discussion replies
                self.db.cursor.execute('''
                    DELETE FROM discussion_replies WHERE discussion_id = ?
                ''', (disc_id,))
                
                # Delete the discussion
                self.db.cursor.execute('''
                    DELETE FROM discussions WHERE id = ?
                ''', (disc_id,))
            
            # Delete associated reviews
            self.db.cursor.execute('''
                DELETE FROM reviews WHERE book_id = ?
            ''', (book_id,))
            
            # Delete from user libraries
            self.db.cursor.execute('''
                DELETE FROM user_library WHERE book_id = ?
            ''', (book_id,))
            
            # Delete the book
            self.db.cursor.execute('''
                DELETE FROM books WHERE id = ?
            ''', (book_id,))
            
            self.db.conn.commit()
            messagebox.showinfo("Success", f"Book '{title}' has been deleted successfully.")
            
            # Refresh books list
            self.show_tech_support_section("books")
            
        except Exception as e:
            messagebox.showerror("Error", f"Failed to delete book: {str(e)}")
    
    def tech_delete_review(self, review_id):
        """Delete a review as tech support"""
        if not messagebox.askyesno("Confirm Deletion", "Are you sure you want to delete this review?"):
            return
            
        try:
            self.db.cursor.execute('''
                DELETE FROM reviews WHERE id = ?
            ''', (review_id,))
            
            self.db.conn.commit()
            messagebox.showinfo("Success", "Review has been deleted successfully.")
            
            # Refresh reviews list
            self.show_tech_support_section("reviews")
            
        except Exception as e:
            messagebox.showerror("Error", f"Failed to delete review: {str(e)}")
    
    def tech_delete_discussion(self, discussion_id):
        """Delete a discussion as tech support"""
        if not messagebox.askyesno("Confirm Deletion", "Are you sure you want to delete this discussion?\nThis will also delete all replies to this discussion."):
            return
            
        try:
            # Delete discussion replies
            self.db.cursor.execute('''
                DELETE FROM discussion_replies WHERE discussion_id = ?
            ''', (discussion_id,))
            
            # Delete the discussion
            self.db.cursor.execute('''
                DELETE FROM discussions WHERE id = ?
            ''', (discussion_id,))
            
            self.db.conn.commit()
            messagebox.showinfo("Success", "Discussion has been deleted successfully.")
            
            # Refresh discussions list
            self.show_tech_support_section("discussions")
            
        except Exception as e:
            messagebox.showerror("Error", f"Failed to delete discussion: {str(e)}")

    def toggle_tech_support_view(self, view_type):
        """Toggle between active and resolved queries view"""
        if view_type == self.current_view:
            return
            
        self.current_view = view_type
        
        # Update button styling
        if view_type == "active":
            self.active_btn.config(bg=self.colors["button_primary"])
            self.resolved_btn.config(bg=self.colors["button_secondary"])
        else:
            self.active_btn.config(bg=self.colors["button_secondary"])
            self.resolved_btn.config(bg=self.colors["button_primary"])
        
        # Load appropriate queries
        self.load_tech_support_queries()
    
    def load_tech_support_queries(self):
        """Load either active or resolved queries based on current view"""
        # Clear existing content
        for widget in self.queries_container.winfo_children():
            widget.destroy()
            
        # Add scrollbar
        scrollbar = ttk.Scrollbar(self.queries_container)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        # Create canvas for queries
        canvas = tk.Canvas(self.queries_container, yscrollcommand=scrollbar.set, bg=self.colors["background"])
        canvas.pack(side=tk.LEFT, fill="both", expand=True)
        
        scrollbar.config(command=canvas.yview)
        
        # Create frame inside canvas
        support_queries_frame = ttk.Frame(canvas)
        canvas.create_window((0, 0), window=support_queries_frame, anchor="nw")
        
        # Get queries based on current view
        if self.current_view == "active":
            self.db.cursor.execute('''
                SELECT sq.id, sq.user_email, u.username, sq.subject, sq.content, sq.status, sq.created_at
                FROM support_queries sq
                JOIN users u ON sq.user_email = u.email
                WHERE sq.status != 'Resolved'
                ORDER BY sq.created_at DESC
            ''')
        else:
            self.db.cursor.execute('''
                SELECT sq.id, sq.user_email, u.username, sq.subject, sq.content, sq.status, sq.created_at
                FROM support_queries sq
                JOIN users u ON sq.user_email = u.email
                WHERE sq.status = 'Resolved'
                ORDER BY sq.created_at DESC
            ''')
        
        queries = self.db.cursor.fetchall()
        
        if not queries:
            status_type = "active" if self.current_view == "active" else "resolved"
            no_queries_label = ttk.Label(support_queries_frame, 
                                      text=f"No {status_type} support queries available.",
                                      font=("Segoe UI", 12))
            no_queries_label.pack(pady=20)
        else:
            # Display queries
            for query_id, user_email, username, subject, content, status, created_at in queries:
                query_frame = ttk.Frame(support_queries_frame)
                query_frame.pack(fill="x", padx=10, pady=10)
                
                # Query header
                header_frame = ttk.Frame(query_frame)
                header_frame.pack(fill="x")
                
                subject_label = ttk.Label(header_frame,
                                        text=f"Subject: {subject}",
                                        font=("Garamond", 14, "bold"))
                subject_label.pack(side=tk.LEFT)
                
                status_color = "#5cb85c" if status == "Resolved" else "#f0ad4e"
                status_label = ttk.Label(header_frame,
                                       text=f"Status: {status}",
                                       font=("Garamond", 12),
                                       foreground=status_color)
                status_label.pack(side=tk.RIGHT)
                
                # Query content
                content_label = ttk.Label(query_frame,
                                        text=content,
                                        wraplength=700)
                content_label.pack(pady=5, anchor="w")
                
                # User info
                user_label = ttk.Label(query_frame,
                                     text=f"From: {username} ({user_email}) on {created_at}",
                                     font=("Garamond", 10, "italic"))
                user_label.pack(anchor="w")
                
                # Show existing responses
                self.db.cursor.execute('''
                    SELECT sr.content, u.username, sr.created_at
                    FROM support_responses sr
                    LEFT JOIN users u ON sr.tech_support_email = u.email
                    WHERE sr.query_id = ?
                    ORDER BY sr.created_at
                ''', (query_id,))
                
                responses = self.db.cursor.fetchall()
                
                if responses:
                    # Response section
                    response_section = ttk.Frame(query_frame)
                    response_section.pack(fill="x", pady=5)
                    
                    ttk.Label(response_section,
                            text="Previous Responses:",
                            font=("Garamond", 12, "bold")).pack(anchor="w")
                    
                    # Display each response
                    for response_content, tech_username, response_date in responses:
                        tech_name = tech_username if tech_username else "Tech Support"
                        response_frame = ttk.Frame(response_section)
                        response_frame.pack(fill="x", pady=5)
                        
                        # Response meta
                        ttk.Label(response_frame,
                                text=f"From: {tech_name} on {response_date}",
                                font=("Garamond", 10, "italic")).pack(anchor="w")
                        
                        # Response content
                        ttk.Label(response_frame,
                                text=response_content,
                                wraplength=650).pack(padx=15, pady=5, anchor="w")
                
                # Only show action buttons for active queries
                if self.current_view == "active":
                    # Button frame
                    button_frame = ttk.Frame(query_frame)
                    button_frame.pack(fill="x", pady=5)
                    
                    # Respond button
                    respond_btn = tk.Button(button_frame,
                                          text="Respond",
                                          command=lambda q=query_id, u=user_email: self.respond_to_query(q, u),
                                          bg=self.colors["button_primary"],
                                          fg="white",
                                          font=("Garamond", 12),
                                          relief=tk.FLAT)
                    respond_btn.pack(side=tk.LEFT, padx=5)
                    
                    # Mark as resolved button
                    if status != "Resolved":
                        resolve_btn = tk.Button(button_frame,
                                              text="Mark as Resolved",
                                              command=lambda q=query_id: self.mark_query_resolved(q),
                                              bg=self.colors["button_secondary"],
                                              fg="white",
                                              font=("Garamond", 12),
                                              relief=tk.FLAT)
                        resolve_btn.pack(side=tk.LEFT, padx=5)
                
                # Add separator between queries
                ttk.Separator(support_queries_frame, orient="horizontal").pack(fill="x", pady=5)
        
        # Update canvas scroll region
        support_queries_frame.update_idletasks()
        canvas.config(scrollregion=canvas.bbox("all"))

    def show_resolved_queries(self):
        """This method is replaced by toggle_tech_support_view and load_tech_support_queries"""
        pass

    def respond_to_query(self, query_id, user_email):
        """Open a window to respond to a support query"""
        response_window = tk.Toplevel(self.root)
        response_window.title("Respond to Support Query")
        response_window.geometry("600x400")
        response_window.configure(bg=self.colors["background"])
        
        # Get query details
        self.db.cursor.execute('''
            SELECT subject, content
            FROM support_queries
            WHERE id = ?
        ''', (query_id,))
        
        subject, content = self.db.cursor.fetchone()
        
        # Display query details
        ttk.Label(response_window, 
                text=f"Query: {subject}",
                font=("Segoe UI", 14, "bold")).pack(pady=10)
        
        query_frame = ttk.Frame(response_window)
        query_frame.pack(fill="x", padx=20, pady=10)
        
        ttk.Label(query_frame,
                text=content,
                wraplength=550).pack()
        
        # Separator
        ttk.Separator(response_window, orient="horizontal").pack(fill="x", padx=20, pady=10)
        
        # Response area
        ttk.Label(response_window,
                text="Your Response:",
                font=("Segoe UI", 12, "bold")).pack(anchor="w", padx=20, pady=5)
        
        response_text = tk.Text(response_window, height=8, width=60)
        response_text.pack(padx=20, pady=10, fill="both", expand=True)
        
        # Button frame
        button_frame = ttk.Frame(response_window)
        button_frame.pack(fill="x", padx=20, pady=10)
        
        # Submit button
        submit_btn = tk.Button(button_frame,
                             text="Submit Response",
                             command=lambda: self.submit_response(query_id, response_text.get("1.0", tk.END).strip(), response_window),
                             bg=self.colors["button_primary"],
                             fg="white",
                             font=("Segoe UI", 11),
                             relief=tk.FLAT)
        submit_btn.pack(side=tk.RIGHT, padx=5)
        
        # Cancel button
        cancel_btn = tk.Button(button_frame,
                             text="Cancel",
                             command=response_window.destroy,
                             bg=self.colors["button_secondary"],
                             fg="white",
                             font=("Segoe UI", 11),
                             relief=tk.FLAT)
        cancel_btn.pack(side=tk.RIGHT, padx=5)

    def submit_response(self, query_id, response_content, response_window):
        """Submit response to a support query"""
        if not response_content:
            messagebox.showerror("Error", "Response cannot be empty")
            return
        
        try:
            # Insert response
            self.db.cursor.execute('''
                INSERT INTO support_responses (query_id, tech_support_email, content)
                VALUES (?, ?, ?)
            ''', (query_id, self.current_user, response_content))
            
            # Mark query as In Progress
            self.db.cursor.execute('''
                UPDATE support_queries
                SET status = 'In Progress'
                WHERE id = ?
            ''', (query_id,))
            
            self.db.conn.commit()
            messagebox.showinfo("Success", "Response submitted successfully")
            response_window.destroy()
            
            # Refresh the tech support interface
            self.show_tech_support_interface()
            
        except Exception as e:
            messagebox.showerror("Error", f"Failed to submit response: {str(e)}")

    def mark_query_resolved(self, query_id):
        """Mark a support query as resolved"""
        try:
            self.db.cursor.execute('''
                UPDATE support_queries
                SET status = 'Resolved'
                WHERE id = ?
            ''', (query_id,))
            
            self.db.conn.commit()
            messagebox.showinfo("Success", "Query marked as resolved")
            
            # Refresh the tech support interface
            self.show_tech_support_interface()
            
        except Exception as e:
            messagebox.showerror("Error", f"Failed to update query status: {str(e)}")
    
    def check_for_badges(self, book_id):
        """Check and award badges based on user activity"""
        try:
            # Get current counts
            self.db.cursor.execute('''
                SELECT books_read, reading_streak
                FROM users
                WHERE email = ?
            ''', (self.current_user,))
            
            books_read, reading_streak = self.db.cursor.fetchone()
            
            # Check for reading badges
            if books_read >= 5 and not self.has_badge("reader", "bookverse"):
                self.award_badge("reader", "bookverse", "Read 5 books")
            
            if books_read >= 10 and not self.has_badge("reader", "Bibliophile"):
                self.award_badge("reader", "Bibliophile", "Read 10 books")
            
            # Check for streak badges
            if reading_streak >= 3 and not self.has_badge("reader", "Consistent Reader"):
                self.award_badge("reader", "Consistent Reader", "3-day reading streak")
            
            if reading_streak >= 7 and not self.has_badge("reader", "Dedicated Reader"):
                self.award_badge("reader", "Dedicated Reader", "7-day reading streak")
            
            # Check for review badges
            self.db.cursor.execute('''
                SELECT COUNT(*) FROM reviews
                WHERE user_email = ?
            ''', (self.current_user,))
            
            review_count = self.db.cursor.fetchone()[0]
            
            if review_count >= 3 and not self.has_badge("reviewer", "Reviewer"):
                self.award_badge("reviewer", "Reviewer", "Posted 3 reviews")
            
            if review_count >= 10 and not self.has_badge("reviewer", "Critic"):
                self.award_badge("reviewer", "Critic", "Posted 10 reviews")
            
        except Exception as e:
            print(f"Error checking for badges: {str(e)}")
    
    def has_badge(self, badge_type, badge_name):
        """Check if user already has a specific badge"""
        self.db.cursor.execute('''
            SELECT COUNT(*) FROM user_badges
            WHERE user_email = ? AND badge_type = ? AND badge_name = ?
        ''', (self.current_user, badge_type, badge_name))
        
        return self.db.cursor.fetchone()[0] > 0
    
    def award_badge(self, badge_type, badge_name, description=""):
        """Award a badge to the user and show a notification"""
        try:
            self.db.cursor.execute('''
                INSERT INTO user_badges (user_email, badge_type, badge_name)
                VALUES (?, ?, ?)
            ''', (self.current_user, badge_type, badge_name))
            
            self.db.conn.commit()
            
            # Show a special toast notification for badge
            self.show_toast(f"🎉 New Achievement: {badge_name}!", "success")
            
        except Exception as e:
            print(f"Error awarding badge: {str(e)}")

    def show_tech_settings_section(self):
        """Show the settings section with various application options"""
        # Create a container for settings
        settings_container = ttk.Frame(self.tech_content_frame)
        settings_container.pack(fill="both", expand=True, padx=20, pady=10)
        
        # Create sections for different types of settings
        app_settings_frame = ttk.Frame(settings_container, style="Card.TFrame")
        app_settings_frame.pack(fill="x", pady=10, padx=10)
        self.apply_shadow_effect(app_settings_frame)
        
        # App settings header
        app_settings_label = ttk.Label(app_settings_frame,
                                    text="Application Settings",
                                    font=("Garamond", 14, "bold"),
                                    foreground=self.colors["primary"],
                                    background=self.colors["card_bg"])
        app_settings_label.pack(anchor="w", padx=15, pady=(15, 10))
        
        # Theme toggle
        theme_frame = ttk.Frame(app_settings_frame, style="Card.TFrame")
        theme_frame.pack(fill="x", padx=15, pady=5)
        
        theme_label = ttk.Label(theme_frame,
                             text="Theme:",
                             font=("Segoe UI", 12),
                             background=self.colors["card_bg"])
        theme_label.pack(side=tk.LEFT, padx=(0, 10))
        
        theme_toggle_btn = tk.Button(theme_frame,
                                  text="Toggle Light/Dark Mode",
                                  command=self.toggle_theme,
                                  bg=self.colors["button_secondary"],
                                  fg="white",
                                  font=("Quicksand", 10),
                                  relief=tk.FLAT,
                                  cursor="hand2")
        theme_toggle_btn.pack(side=tk.LEFT)
        
        # About button
        about_frame = ttk.Frame(app_settings_frame, style="Card.TFrame")
        about_frame.pack(fill="x", padx=15, pady=5)
        
        about_label = ttk.Label(about_frame,
                             text="About:",
                             font=("Segoe UI", 12),
                             background=self.colors["card_bg"])
        about_label.pack(side=tk.LEFT, padx=(0, 10))
        
        about_btn = tk.Button(about_frame,
                           text="View Application Info",
                           command=self.show_about,
                           bg=self.colors["button_secondary"],
                           fg="white",
                           font=("Quicksand", 10),
                           relief=tk.FLAT,
                           cursor="hand2")
        about_btn.pack(side=tk.LEFT, padx=10)
        
        # Exit button
        exit_frame = ttk.Frame(app_settings_frame, style="Card.TFrame")
        exit_frame.pack(fill="x", padx=15, pady=(5, 15))
        
        exit_label = ttk.Label(exit_frame,
                            text="Exit:",
                            font=("Segoe UI", 12),
                            background=self.colors["card_bg"])
        exit_label.pack(side=tk.LEFT, padx=(0, 10))
        
        exit_btn = tk.Button(exit_frame,
                          text="Exit Application",
                          command=self.root.quit,
                          bg=self.colors["button_primary"],
                          fg="white",
                          font=("Quicksand", 10),
                          relief=tk.FLAT,
                          cursor="hand2")
        exit_btn.pack(side=tk.LEFT, padx=10)
        
        # User settings
        user_settings_frame = ttk.Frame(settings_container, style="Card.TFrame")
        user_settings_frame.pack(fill="x", pady=10, padx=10)
        self.apply_shadow_effect(user_settings_frame)
        
        user_settings_label = ttk.Label(user_settings_frame,
                                     text="User Settings",
                                     font=("Garamond", 14, "bold"),
                                     foreground=self.colors["primary"],
                                     background=self.colors["card_bg"])
        user_settings_label.pack(anchor="w", padx=15, pady=(15, 10))
        
        # Logout button
        logout_frame = ttk.Frame(user_settings_frame, style="Card.TFrame")
        logout_frame.pack(fill="x", padx=15, pady=(5, 15))
        
        logout_label = ttk.Label(logout_frame,
                              text="Session:",
                              font=("Segoe UI", 12),
                              background=self.colors["card_bg"])
        logout_label.pack(side=tk.LEFT, padx=(0, 10))
        
        logout_btn = tk.Button(logout_frame,
                            text="Logout",
                            command=self.logout,
                            bg=self.colors["button_primary"],
                            fg="white",
                            font=("Quicksand", 10),
                            relief=tk.FLAT,
                            cursor="hand2")
        logout_btn.pack(side=tk.LEFT, padx=10)

    def paste_from_clipboard_to_entry(self, entry_widget):
        """Safely paste clipboard content to an entry widget"""
        try:
            clipboard_content = self.root.clipboard_get()
            entry_widget.delete(0, tk.END)
            entry_widget.insert(0, clipboard_content)
        except Exception as e:
            self.show_toast("Clipboard is empty or contains non-text content", "warning")

    def create_cozy_corner_image(self, width, height):
        """Create a cozy reading corner image"""
        img = Image.new('RGBA', (width, height), (255, 0, 0, 0))
        draw = ImageDraw.Draw(img)
        
        # Background wall color - warm beige
        wall_color = (245, 222, 179)
        draw.rectangle([0, 0, width, height], fill=wall_color)
        
        # Add subtle texture to wall
        for i in range(1000):
            x = random.randint(0, width)
            y = random.randint(0, height)
            r, g, b = wall_color
            variation = random.randint(-10, 10)
            texture_color = (r + variation, g + variation, b + variation)
            draw.point([x, y], fill=texture_color)
        
        # Floor (wooden)
        floor_color = (160, 120, 90)
        draw.rectangle([0, 2*height//3, width, height], fill=floor_color)
        
        # Add wooden planks to floor
        for i in range(20):
            y = 2*height//3 + i * 20
            if y < height:
                plank_color = (floor_color[0] + random.randint(-20, 20),
                             floor_color[1] + random.randint(-20, 20),
                             floor_color[2] + random.randint(-20, 20))
                draw.rectangle([0, y, width, y + 15], fill=plank_color)
        
        # Cozy reading nook - large bookshelf on the left
        bookshelf_color = (120, 80, 40)
        draw.rectangle([50, 100, 300, 2*height//3], fill=bookshelf_color)
        
        # Bookshelf shelves
        shelf_color = (140, 100, 60)
        for i in range(4):
            y = 150 + i * 100
            if y < 2*height//3:
                draw.rectangle([50, y, 300, y + 10], fill=shelf_color)
        
        # Books on shelves
        book_colors = [
            (210, 105, 30),  # Chocolate
            (165, 42, 42),   # Brown
            (128, 0, 0),     # Maroon
            (255, 69, 0),    # Orange Red
            (255, 215, 0),   # Gold
            (189, 183, 107), # Dark Khaki
            (85, 107, 47),   # Dark Olive Green
            (46, 139, 87),   # Sea Green
            (70, 130, 180),  # Steel Blue
            (25, 25, 112),   # Midnight Blue
            (138, 43, 226),  # Blue Violet
            (199, 21, 133),  # Medium Violet Red
        ]
        
        for shelf_num in range(4):
            y_pos = 150 + shelf_num * 100
            if y_pos < 2*height//3:
                x_pos = 60
                while x_pos < 290:
                    book_width = random.randint(15, 30)
                    book_height = random.randint(70, 90)
                    book_color = random.choice(book_colors)
                    
                    if x_pos + book_width < 290:
                        # Draw book
                        draw.rectangle([x_pos, y_pos - book_height, x_pos + book_width, y_pos], 
                                    fill=book_color)
                        x_pos += book_width + 2
                    else:
                        break
        
        # Reading chair
        chair_color = (160, 82, 45)  # Sienna
        # Chair back
        draw.rectangle([width - 300, height//2, width - 200, 2*height//3], fill=chair_color)
        # Chair seat
        draw.rectangle([width - 300, 2*height//3, width - 100, 2*height//3 + 50], fill=chair_color)
        # Chair arm
        draw.rectangle([width - 300, 2*height//3 - 20, width - 280, 2*height//3 + 30], fill=chair_color)
        
        # Reading lamp
        lamp_base_color = (80, 60, 40)
        lamp_shade_color = (255, 223, 170, 200)
        # Lamp stand
        draw.rectangle([width - 350, 2*height//3 - 150, width - 340, 2*height//3], fill=lamp_base_color)
        # Lamp base
        draw.ellipse([width - 360, 2*height//3 - 10, width - 330, 2*height//3 + 10], fill=lamp_base_color)
        # Lamp shade
        draw.chord([width - 380, 2*height//3 - 200, width - 310, 2*height//3 - 150], 0, 180, fill=lamp_shade_color)
        
        # Lamp glow effect
        for radius in range(100, 0, -10):
            alpha = int(100 * radius / 100)
            glow_color = (255, 255, 200, alpha)
            draw.ellipse([
                width - 345 - radius, 2*height//3 - 175 - radius,
                width - 345 + radius, 2*height//3 - 175 + radius
            ], fill=glow_color)
        
        # Window with outdoor scene
        window_frame_color = (120, 80, 40)
        draw.rectangle([width//2 - 100, 100, width//2 + 100, 300], fill=window_frame_color)
        
        # Window glass (with outdoor scene - blue sky)
        sky_color = (135, 206, 235)
        draw.rectangle([width//2 - 90, 110, width//2 + 90, 290], fill=sky_color)
        
        # Window panes
        draw.line([width//2, 110, width//2, 290], fill=window_frame_color, width=4)
        draw.line([width//2 - 90, 200, width//2 + 90, 200], fill=window_frame_color, width=4)
        
        # Some clouds in the window
        cloud_color = (255, 255, 255, 180)
        draw.ellipse([width//2 - 80, 130, width//2 - 40, 150], fill=cloud_color)
        draw.ellipse([width//2 - 60, 120, width//2 - 20, 145], fill=cloud_color)
        draw.ellipse([width//2 + 20, 150, width//2 + 70, 180], fill=cloud_color)
        draw.ellipse([width//2 + 30, 140, width//2 + 80, 170], fill=cloud_color)
        
        # Little table with a steaming cup
        table_color = (120, 80, 40)
        draw.rectangle([width - 400, 2*height//3 - 30, width - 300, 2*height//3], fill=table_color)
        draw.rectangle([width - 370, 2*height//3, width - 330, 2*height//3 + 50], fill=table_color)
        
        # Coffee cup on table
        cup_color = (255, 255, 255)
        draw.ellipse([width - 365, 2*height//3 - 25, width - 335, 2*height//3 - 5], fill=cup_color)
        draw.rectangle([width - 365, 2*height//3 - 20, width - 335, 2*height//3 - 5], fill=cup_color)
        
        # Coffee in cup
        coffee_color = (101, 67, 33)
        draw.ellipse([width - 360, 2*height//3 - 20, width - 340, 2*height//3 - 10], fill=coffee_color)
        
        # Steam from coffee
        steam_color = (255, 255, 255, 150)
        for i in range(3):
            x_offset = width - 350 + (i-1) * 5
            for j in range(3):
                draw.arc([x_offset - 5, 2*height//3 - 30 - j*5, 
                        x_offset + 5, 2*height//3 - 20 - j*5], 
                       180, 0, fill=steam_color, width=1)
        
        # Reading book on the chair
        book_color = (139, 69, 19)  # Saddle brown
        draw.rectangle([width - 250, 2*height//3 - 10, width - 150, 2*height//3 + 10], fill=book_color)
        
        # Book pages
        page_color = (255, 250, 240)  # Floral white
        draw.rectangle([width - 248, 2*height//3 - 8, width - 152, 2*height//3 - 2], fill=page_color)
        
        # A cat sleeping on the chair
        cat_color = (255, 165, 79)  # Orange
        # Cat body
        draw.ellipse([width - 220, 2*height//3 + 10, width - 150, 2*height//3 + 40], fill=cat_color)
        # Cat head
        draw.ellipse([width - 160, 2*height//3 + 5, width - 130, 2*height//3 + 35], fill=cat_color)
        # Cat tail
        draw.arc([width - 240, 2*height//3, width - 180, 2*height//3 + 20], 
               180, 270, fill=cat_color, width=8)
        
        # Add a cozy rug
        rug_color = (180, 30, 30)  # Reddish
        draw.ellipse([width//2 - 200, 2*height//3 - 50, width//2 + 200, 2*height//3 + 150], 
                   fill=rug_color, outline=(150, 20, 20), width=5)
        
        # Add rug pattern
        pattern_color = (220, 100, 100)
        for i in range(3):
            radius = 150 - i * 40
            if radius > 0:
                draw.ellipse([
                    width//2 - radius, 2*height//3 + 50 - radius,
                    width//2 + radius, 2*height//3 + 50 + radius
                ], outline=pattern_color, width=3)
        
        # Add a soft blur to the entire image for a dreamy effect
        img = img.filter(ImageFilter.GaussianBlur(radius=1))
        
        return img

def center_window(window, width=1024, height=768):
    """Center a tkinter window on the screen"""
    # Get screen width and height
    screen_width = window.winfo_screenwidth()
    screen_height = window.winfo_screenheight()
    
    # Calculate position x and y coordinates
    x = (screen_width - width) // 2
    y = (screen_height - height) // 2
    
    window.geometry(f"{width}x{height}+{x}+{y}")

if __name__ == "__main__":
    root = tk.Tk()
    root.title("BookVerse Reader")
    center_window(root, 1024, 768)
    
    # Set window icon if available
    try:
        icon_path = os.path.join("assets", "icon.ico")
        if os.path.exists(icon_path):
            root.iconbitmap(icon_path)
    except Exception:
        pass
        
    app = bookverseApp(root)
    root.mainloop()
