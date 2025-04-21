from flask import Flask, render_template, redirect, url_for, flash, request, jsonify, session
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
import os
from datetime import datetime
import base64
from PIL import Image, ImageDraw, ImageFilter
import io
import random

# Initialize Flask app
app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'dev-key-for-testing')
app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('DATABASE_URL', 'sqlite:///bookverse.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['UPLOAD_FOLDER'] = os.path.join(os.getcwd(), 'static', 'uploads')
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max upload

# Ensure upload directory exists
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

# Initialize extensions
db = SQLAlchemy(app)
login_manager = LoginManager(app)
login_manager.login_view = 'login'

# Models
class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(120), unique=True, nullable=False)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password_hash = db.Column(db.String(128))
    full_name = db.Column(db.String(100))
    user_type = db.Column(db.String(20), default='reader')
    avatar = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    books = db.relationship('Book', backref='author', lazy=True)
    
    def set_password(self, password):
        self.password_hash = generate_password_hash(password)
        
    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

class Book(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text)
    author_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    pdf_data = db.Column(db.LargeBinary)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    amazon_link = db.Column(db.String(255))
    reviews = db.relationship('Review', backref='book', lazy=True)
    discussions = db.relationship('Discussion', backref='book', lazy=True)

class UserLibrary(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    book_id = db.Column(db.Integer, db.ForeignKey('book.id'), nullable=False)
    added_at = db.Column(db.DateTime, default=datetime.utcnow)
    user = db.relationship('User', backref=db.backref('library', lazy=True))
    book = db.relationship('Book')

class Review(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    book_id = db.Column(db.Integer, db.ForeignKey('book.id'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    rating = db.Column(db.Integer, nullable=False)
    comment = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    user = db.relationship('User', backref=db.backref('reviews', lazy=True))

class Discussion(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    book_id = db.Column(db.Integer, db.ForeignKey('book.id'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    title = db.Column(db.String(200), nullable=False)
    content = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    user = db.relationship('User', backref=db.backref('discussions', lazy=True))
    replies = db.relationship('DiscussionReply', backref='discussion', lazy=True)

class DiscussionReply(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    discussion_id = db.Column(db.Integer, db.ForeignKey('discussion.id'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    content = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    user = db.relationship('User', backref=db.backref('replies', lazy=True))

class SupportQuery(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    subject = db.Column(db.String(200), nullable=False)
    message = db.Column(db.Text, nullable=False)
    status = db.Column(db.String(20), default='open')
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    response = db.Column(db.Text)
    user = db.relationship('User', backref=db.backref('queries', lazy=True))

class Badge(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    badge_type = db.Column(db.String(50), nullable=False)
    badge_name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text)
    awarded_at = db.Column(db.DateTime, default=datetime.utcnow)
    user = db.relationship('User', backref=db.backref('badges', lazy=True))

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# Helper functions
def create_cozy_corner_image(width=500, height=300):
    """Create a cozy reading corner image for the home page"""
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
    
    # Books on shelves with various colors
    book_colors = [
        (210, 105, 30), (165, 42, 42), (128, 0, 0), (255, 69, 0),
        (255, 215, 0), (189, 183, 107), (85, 107, 47), (46, 139, 87),
        (70, 130, 180), (25, 25, 112), (138, 43, 226), (199, 21, 133)
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
    
    # Apply a soft blur for a dreamy effect
    img = img.filter(ImageFilter.GaussianBlur(radius=1))
    
    # Convert to base64 for embedding in HTML
    buffered = io.BytesIO()
    img.save(buffered, format="PNG")
    img_str = base64.b64encode(buffered.getvalue()).decode('utf-8')
    
    return f"data:image/png;base64,{img_str}"

def generate_avatar(username, email, width=100, height=100):
    """Generate an avatar based on user initials"""
    img = Image.new('RGB', (width, height), color=(73, 109, 137))
    d = ImageDraw.Draw(img)
    
    # Get initials from username or email
    if username:
        initials = username[0].upper()
    else:
        initials = email[0].upper()
    
    # Calculate text position and size
    font_size = int(width / 2)
    d.text((width/2, height/2), initials, fill=(255, 255, 255), anchor="mm")
    
    # Convert to base64 for embedding in HTML
    buffered = io.BytesIO()
    img.save(buffered, format="PNG")
    img_str = base64.b64encode(buffered.getvalue()).decode('utf-8')
    
    return f"data:image/png;base64,{img_str}"

def add_sample_data():
    """Add sample books and users for testing"""
    if User.query.count() == 0:
        # Create admin user
        admin = User(
            email='admin@bookverse.com',
            username='admin',
            full_name='Admin User',
            user_type='admin'
        )
        admin.set_password('admin123')
        
        # Create author user
        author = User(
            email='author@bookverse.com',
            username='author',
            full_name='Sample Author',
            user_type='author'
        )
        author.set_password('author123')
        
        # Create reader user
        reader = User(
            email='reader@bookverse.com',
            username='reader',
            full_name='Sample Reader',
            user_type='reader'
        )
        reader.set_password('reader123')
        
        # Create tech support user
        tech_support = User(
            email='support@bookverse.com',
            username='support',
            full_name='Tech Support',
            user_type='tech_support'
        )
        tech_support.set_password('support123')
        
        db.session.add_all([admin, author, reader, tech_support])
        db.session.commit()
        
        # Add sample books
        sample_descriptions = [
            "A thrilling adventure through time and space that will keep you on the edge of your seat.",
            "A heartwarming tale of friendship and coming of age in a small town.",
            "A deep exploration of human consciousness and what it means to be alive."
        ]
        
        for i in range(3):
            book = Book(
                title=f"Sample Book {i+1}",
                description=sample_descriptions[i],
                author_id=author.id,
                amazon_link=f"https://amazon.com/sample-book-{i+1}"
            )
            db.session.add(book)
        
        db.session.commit()

# Routes
@app.route('/')
def index():
    if current_user.is_authenticated:
        if current_user.user_type == 'reader':
            return redirect(url_for('browse'))
        elif current_user.user_type == 'author':
            return redirect(url_for('author_dashboard'))
        elif current_user.user_type == 'admin':
            return redirect(url_for('admin_dashboard'))
    
    cozy_corner = create_cozy_corner_image()
    return render_template('index.html', cozy_corner=cozy_corner)

@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('index'))
    
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        
        user = User.query.filter_by(email=email).first()
        if user is None or not user.check_password(password):
            flash('Invalid email or password', 'error')
            return redirect(url_for('login'))
        
        login_user(user)
        next_page = request.args.get('next')
        if not next_page or not next_page.startswith('/'):
            next_page = url_for('index')
        return redirect(next_page)
    
    return render_template('login.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('index'))
    
    if request.method == 'POST':
        email = request.form.get('email')
        username = request.form.get('username')
        password = request.form.get('password')
        full_name = request.form.get('full_name')
        user_type = request.form.get('user_type', 'reader')
        
        if User.query.filter_by(email=email).first():
            flash('Email already registered', 'error')
            return redirect(url_for('register'))
        
        if User.query.filter_by(username=username).first():
            flash('Username already taken', 'error')
            return redirect(url_for('register'))
        
        user = User(email=email, username=username, full_name=full_name, user_type=user_type)
        user.set_password(password)
        user.avatar = generate_avatar(username, email)
        
        db.session.add(user)
        db.session.commit()
        
        flash('Account created successfully. Please log in.', 'success')
        return redirect(url_for('login'))
    
    return render_template('register.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('index'))

@app.route('/browse')
@login_required
def browse():
    books = Book.query.join(User).add_columns(
        Book.id, Book.title, Book.description, Book.amazon_link,
        User.username, User.id.label('author_id')
    ).all()
    
    return render_template('browse.html', books=books)

@app.route('/book/<int:book_id>')
@login_required
def view_book(book_id):
    book = Book.query.get_or_404(book_id)
    author = User.query.get(book.author_id)
    reviews = Review.query.filter_by(book_id=book_id).all()
    
    # Calculate average rating
    avg_rating = 0
    if reviews:
        total = sum(review.rating for review in reviews)
        avg_rating = total / len(reviews)
    
    in_library = False
    if current_user.is_authenticated:
        library_entry = UserLibrary.query.filter_by(
            user_id=current_user.id, book_id=book_id
        ).first()
        in_library = library_entry is not None
    
    return render_template('book.html', 
                           book=book, 
                           author=author,
                           reviews=reviews,
                           avg_rating=avg_rating,
                           in_library=in_library)

@app.route('/book/<int:book_id>/read')
@login_required
def read_book(book_id):
    book = Book.query.get_or_404(book_id)
    
    # Check if PDF data exists
    if not book.pdf_data:
        flash('No PDF data available for this book', 'error')
        return redirect(url_for('view_book', book_id=book_id))
    
    # Generate a temporary file path for the PDF
    pdf_path = f'/static/temp/{book_id}.pdf'
    physical_path = os.path.join(app.root_path, 'static/temp', f'{book_id}.pdf')
    
    # Ensure the directory exists
    os.makedirs(os.path.dirname(physical_path), exist_ok=True)
    
    # Write the PDF data to the file
    with open(physical_path, 'wb') as f:
        f.write(book.pdf_data)
    
    return render_template('read.html', book=book, pdf_path=pdf_path)

@app.route('/library')
@login_required
def library():
    library_books = UserLibrary.query.filter_by(user_id=current_user.id).all()
    books = []
    
    for entry in library_books:
        book = Book.query.get(entry.book_id)
        author = User.query.get(book.author_id)
        books.append({
            'id': book.id,
            'title': book.title,
            'description': book.description,
            'author': author.username,
            'added_at': entry.added_at
        })
    
    return render_template('library.html', books=books)

@app.route('/library/add/<int:book_id>', methods=['POST'])
@login_required
def add_to_library(book_id):
    book = Book.query.get_or_404(book_id)
    
    # Check if already in library
    existing = UserLibrary.query.filter_by(
        user_id=current_user.id, book_id=book_id
    ).first()
    
    if existing:
        flash('Book already in your library', 'info')
    else:
        library_entry = UserLibrary(user_id=current_user.id, book_id=book_id)
        db.session.add(library_entry)
        db.session.commit()
        flash('Book added to your library', 'success')
    
    return redirect(url_for('view_book', book_id=book_id))

@app.route('/library/remove/<int:book_id>', methods=['POST'])
@login_required
def remove_from_library(book_id):
    library_entry = UserLibrary.query.filter_by(
        user_id=current_user.id, book_id=book_id
    ).first_or_404()
    
    db.session.delete(library_entry)
    db.session.commit()
    flash('Book removed from your library', 'success')
    
    return redirect(url_for('library'))

@app.route('/discussions')
@login_required
def discussions():
    # Get all discussions
    discussions = Discussion.query.order_by(Discussion.created_at.desc()).all()
    
    # Get user's discussions
    user_discussions = Discussion.query.filter_by(user_id=current_user.id).order_by(Discussion.created_at.desc()).all()
    
    return render_template('discussions.html', discussions=discussions, user_discussions=user_discussions)

@app.route('/book/<int:book_id>/discussions')
@login_required
def book_discussions(book_id):
    book = Book.query.get_or_404(book_id)
    discussions = Discussion.query.filter_by(book_id=book_id).order_by(Discussion.created_at.desc()).all()
    
    return render_template('book_discussions.html', book=book, discussions=discussions)

@app.route('/discussion/<int:discussion_id>')
@login_required
def view_discussion(discussion_id):
    discussion = Discussion.query.get_or_404(discussion_id)
    replies = DiscussionReply.query.filter_by(discussion_id=discussion_id).order_by(DiscussionReply.created_at).all()
    
    return render_template('discussion_detail.html', discussion=discussion, replies=replies)

@app.route('/book/<int:book_id>/new-discussion')
@login_required
def new_discussion(book_id):
    book = Book.query.get_or_404(book_id)
    return render_template('new_discussion.html', book=book)

@app.route('/book/<int:book_id>/create-discussion', methods=['POST'])
@login_required
def create_discussion(book_id):
    book = Book.query.get_or_404(book_id)
    
    title = request.form.get('title')
    content = request.form.get('content')
    
    if not title or not content:
        flash('Please fill out all fields', 'error')
        return redirect(url_for('new_discussion', book_id=book_id))
    
    discussion = Discussion(
        title=title,
        content=content,
        user_id=current_user.id,
        book_id=book_id
    )
    
    db.session.add(discussion)
    db.session.commit()
    
    flash('Discussion created successfully', 'success')
    return redirect(url_for('view_discussion', discussion_id=discussion.id))

@app.route('/discussion/<int:discussion_id>/reply', methods=['POST'])
@login_required
def add_reply(discussion_id):
    discussion = Discussion.query.get_or_404(discussion_id)
    
    content = request.form.get('content')
    
    if not content:
        flash('Reply cannot be empty', 'error')
        return redirect(url_for('view_discussion', discussion_id=discussion_id))
    
    reply = DiscussionReply(
        content=content,
        user_id=current_user.id,
        discussion_id=discussion_id
    )
    
    db.session.add(reply)
    db.session.commit()
    
    flash('Reply added successfully', 'success')
    return redirect(url_for('view_discussion', discussion_id=discussion_id))

@app.route('/profile')
@login_required
def profile():
    return render_template('profile.html', user=current_user)

@app.route('/profile/edit', methods=['GET', 'POST'])
@login_required
def edit_profile():
    if request.method == 'POST':
        current_user.full_name = request.form.get('full_name', current_user.full_name)
        
        db.session.commit()
        flash('Profile updated successfully', 'success')
        return redirect(url_for('profile'))
    
    return render_template('edit_profile.html', user=current_user)

@app.route('/toggle_theme', methods=['POST'])
def toggle_theme():
    current_theme = session.get('theme', 'light')
    session['theme'] = 'dark' if current_theme == 'light' else 'light'
    return redirect(request.referrer or url_for('index'))

@app.route('/author/dashboard')
@login_required
def author_dashboard():
    if current_user.user_type != 'author':
        flash('Access denied. Author privileges required.', 'error')
        return redirect(url_for('index'))
    
    books = Book.query.filter_by(author_id=current_user.id).all()
    return render_template('author/dashboard.html', books=books)

@app.route('/author/reviews')
@login_required
def author_reviews():
    if current_user.user_type != 'author':
        flash('Access denied. Author privileges required.', 'error')
        return redirect(url_for('index'))
    
    # Get all reviews for books by this author
    reviews = Review.query.select_from(Review).\
        join(Book, Book.id == Review.book_id).\
        join(User, User.id == Review.user_id).\
        filter(Book.author_id == current_user.id).\
        add_columns(
            Review.id, Review.rating, Review.comment, Review.created_at,
            User.username, Book.title, Book.id.label('book_id')
        ).order_by(Review.created_at.desc()).all()
    
    return render_template('author/reviews.html', reviews=reviews)

@app.route('/author/discussions')
@login_required
def author_discussions():
    if current_user.user_type != 'author':
        flash('Access denied. Author privileges required.', 'error')
        return redirect(url_for('index'))
    
    # Get all discussions for books by this author
    discussions = Discussion.query.select_from(Discussion).\
        join(Book, Book.id == Discussion.book_id).\
        join(User, User.id == Discussion.user_id).\
        filter(Book.author_id == current_user.id).\
        add_columns(
            Discussion.id, Discussion.title, Discussion.content, Discussion.created_at,
            User.username, Book.title.label('book_title'), Book.id.label('book_id')
        ).order_by(Discussion.created_at.desc()).all()
    
    return render_template('author/discussions.html', discussions=discussions)

@app.route('/author/upload', methods=['GET', 'POST'])
@login_required
def upload_book():
    if current_user.user_type != 'author':
        flash('Access denied. Author privileges required.', 'error')
        return redirect(url_for('index'))
    
    if request.method == 'POST':
        title = request.form.get('title')
        description = request.form.get('description')
        amazon_link = request.form.get('amazon_link', '')
        pdf_file = request.files.get('pdf_file')
        
        if not title or not description or not pdf_file:
            flash('Please fill all required fields and upload a PDF file', 'error')
            return redirect(url_for('upload_book'))
        
        if pdf_file.filename == '':
            flash('No file selected', 'error')
            return redirect(url_for('upload_book'))
        
        # Read PDF data
        pdf_data = pdf_file.read()
        
        # Create new book
        book = Book(
            title=title,
            description=description,
            author_id=current_user.id,
            pdf_data=pdf_data,
            amazon_link=amazon_link
        )
        
        db.session.add(book)
        db.session.commit()
        
        flash('Book uploaded successfully', 'success')
        return redirect(url_for('author_dashboard'))
    
    return render_template('author/upload.html')

@app.route('/author/edit/<int:book_id>', methods=['GET', 'POST'])
@login_required
def edit_book(book_id):
    book = Book.query.get_or_404(book_id)
    
    # Check if current user is the author
    if book.author_id != current_user.id and current_user.user_type != 'admin':
        flash('Access denied. You can only edit your own books.', 'error')
        return redirect(url_for('author_dashboard'))
    
    if request.method == 'POST':
        book.title = request.form.get('title', book.title)
        book.description = request.form.get('description', book.description)
        book.amazon_link = request.form.get('amazon_link', book.amazon_link)
        
        pdf_file = request.files.get('pdf_file')
        if pdf_file and pdf_file.filename != '':
            book.pdf_data = pdf_file.read()
        
        db.session.commit()
        flash('Book updated successfully', 'success')
        return redirect(url_for('author_dashboard'))
    
    return render_template('author/edit_book.html', book=book)

@app.route('/author/delete/<int:book_id>', methods=['POST'])
@login_required
def delete_book(book_id):
    book = Book.query.get_or_404(book_id)
    
    # Check if current user is the author
    if book.author_id != current_user.id and current_user.user_type != 'admin':
        flash('Access denied. You can only delete your own books.', 'error')
        return redirect(url_for('author_dashboard'))
    
    # Get book title for the flash message
    book_title = book.title
    
    # Delete the book
    db.session.delete(book)
    db.session.commit()
    
    flash(f'Book "{book_title}" was successfully deleted', 'success')
    return redirect(url_for('author_dashboard'))

@app.route('/admin/dashboard')
@login_required
def admin_dashboard():
    if current_user.user_type != 'admin':
        flash('Access denied. Admin privileges required.', 'error')
        return redirect(url_for('index'))
    
    user_count = User.query.count()
    book_count = Book.query.count()
    review_count = Review.query.count()
    discussion_count = Discussion.query.count()
    
    recent_users = User.query.order_by(User.created_at.desc()).limit(5).all()
    recent_books = Book.query.order_by(Book.created_at.desc()).limit(5).all()
    queries = SupportQuery.query.filter_by(status='open').all()
    
    return render_template('admin/dashboard.html', 
                          user_count=user_count,
                          book_count=book_count,
                          review_count=review_count,
                          discussion_count=discussion_count,
                          recent_users=recent_users,
                          recent_books=recent_books,
                          queries=queries)

@app.route('/admin/reviews')
@login_required
def admin_reviews():
    if current_user.user_type != 'admin':
        flash('Access denied. Admin privileges required.', 'error')
        return redirect(url_for('index'))
    
    reviews = Review.query.select_from(Review).\
        join(User, User.id == Review.user_id).\
        join(Book, Book.id == Review.book_id).\
        add_columns(
            Review.id, Review.rating, Review.comment, Review.created_at,
            User.username, Book.title, Book.id.label('book_id')
        ).order_by(Review.created_at.desc()).all()
    
    return render_template('admin/reviews.html', reviews=reviews)

@app.route('/admin/discussions')
@login_required
def admin_discussions():
    if current_user.user_type != 'admin':
        flash('Access denied. Admin privileges required.', 'error')
        return redirect(url_for('index'))
    
    discussions = Discussion.query.select_from(Discussion).\
        join(User, User.id == Discussion.user_id).\
        join(Book, Book.id == Discussion.book_id).\
        add_columns(
            Discussion.id, Discussion.title, Discussion.content, Discussion.created_at,
            User.username, Book.title.label('book_title'), Book.id.label('book_id')
        ).order_by(Discussion.created_at.desc()).all()
    
    return render_template('admin/discussions.html', discussions=discussions)

@app.route('/admin/review/delete/<int:review_id>', methods=['POST'])
@login_required
def admin_delete_review(review_id):
    if current_user.user_type != 'admin':
        flash('Access denied. Admin privileges required.', 'error')
        return redirect(url_for('index'))
    
    review = Review.query.get_or_404(review_id)
    
    # Store information for the flash message
    book = Book.query.get(review.book_id)
    book_title = book.title if book else "Unknown book"
    username = User.query.get(review.user_id).username if review.user_id else "Unknown user"
    
    # Delete the review
    db.session.delete(review)
    db.session.commit()
    
    flash(f'Review by {username} for "{book_title}" has been deleted', 'success')
    return redirect(url_for('admin_reviews'))

@app.route('/admin/discussion/delete/<int:discussion_id>', methods=['POST'])
@login_required
def admin_delete_discussion(discussion_id):
    if current_user.user_type != 'admin':
        flash('Access denied. Admin privileges required.', 'error')
        return redirect(url_for('index'))
    
    discussion = Discussion.query.get_or_404(discussion_id)
    
    # Store information for the flash message
    book = Book.query.get(discussion.book_id)
    book_title = book.title if book else "Unknown book"
    username = User.query.get(discussion.user_id).username if discussion.user_id else "Unknown user"
    
    # Delete associated replies first (to avoid foreign key constraint violations)
    DiscussionReply.query.filter_by(discussion_id=discussion_id).delete()
    
    # Delete the discussion
    db.session.delete(discussion)
    db.session.commit()
    
    flash(f'Discussion "{discussion.title}" by {username} for "{book_title}" has been deleted', 'success')
    return redirect(url_for('admin_discussions'))

@app.route('/book/<int:book_id>/review', methods=['POST'])
@login_required
def submit_review(book_id):
    book = Book.query.get_or_404(book_id)
    
    rating = request.form.get('rating')
    comment = request.form.get('comment')
    
    if not rating:
        flash('Please provide a rating', 'error')
        return redirect(url_for('view_book', book_id=book_id))
    
    # Check if user already reviewed this book
    existing_review = Review.query.filter_by(
        user_id=current_user.id, book_id=book_id
    ).first()
    
    if existing_review:
        # Update existing review
        existing_review.rating = rating
        existing_review.comment = comment
        db.session.commit()
        flash('Your review has been updated', 'success')
    else:
        # Create new review
        review = Review(
            book_id=book_id,
            user_id=current_user.id,
            rating=int(rating),
            comment=comment
        )
        db.session.add(review)
        db.session.commit()
        flash('Your review has been submitted', 'success')
    
    return redirect(url_for('view_book', book_id=book_id))

@app.route('/book/<int:book_id>/reviews')
@login_required
def book_reviews(book_id):
    book = Book.query.get_or_404(book_id)
    reviews = Review.query.filter_by(book_id=book_id).order_by(Review.created_at.desc()).all()
    
    return render_template('book_reviews.html', book=book, reviews=reviews)

@app.route('/tech_support/dashboard')
@login_required
def tech_support_dashboard():
    if current_user.user_type != 'tech_support':
        flash('Access denied. Tech support access required.', 'error')
        return redirect(url_for('index'))
    
    # Get all support queries
    open_queries = SupportQuery.query.filter_by(status='open').order_by(SupportQuery.created_at.desc()).all()
    resolved_queries = SupportQuery.query.filter_by(status='resolved').order_by(SupportQuery.created_at.desc()).all()
    
    return render_template('tech_support/dashboard.html', 
                          open_queries=open_queries, 
                          resolved_queries=resolved_queries)

@app.route('/tech_support/respond/<int:query_id>', methods=['POST'])
@login_required
def respond_to_query(query_id):
    if current_user.user_type != 'tech_support':
        flash('Access denied. Tech support access required.', 'error')
        return redirect(url_for('index'))
    
    query = SupportQuery.query.get_or_404(query_id)
    response = request.form.get('response')
    
    if not response:
        flash('Response cannot be empty', 'error')
        return redirect(url_for('tech_support_dashboard'))
    
    query.response = response
    query.status = 'resolved'
    db.session.commit()
    
    flash('Response submitted successfully', 'success')
    return redirect(url_for('tech_support_dashboard'))

# Run the app
if __name__ == '__main__':
    with app.app_context():
        db.create_all()
        add_sample_data()
    app.run(debug=True) 