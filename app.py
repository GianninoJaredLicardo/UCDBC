import os
import uuid
from flask import Flask, render_template, request, redirect, url_for, session
from flask_sqlalchemy import SQLAlchemy
from werkzeug.utils import secure_filename

app = Flask(__name__)

app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///uc_corps.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['MAX_CONTENT_LENGTH'] = 8 * 1024 * 1024  # 8 MB upload limit
app.secret_key = 'ucdbc-secret-key-2026'  # Change this to something random in production

ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'webp'}

# ── Admin credentials — change these! ──────────────────────────────
ADMIN_USERNAME = 'admin'
ADMIN_PASSWORD = 'ucdbc'
# ───────────────────────────────────────────────────────────────────

db = SQLAlchemy(app)


def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


class Member(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    section = db.Column(db.String(50), nullable=False)
    instrument = db.Column(db.String(50), nullable=False)


class Performance(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(150), nullable=False)
    date = db.Column(db.String(50), nullable=False)
    location = db.Column(db.String(150), nullable=False)


class GalleryPhoto(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(150), nullable=False)
    year = db.Column(db.String(10), nullable=False)
    category = db.Column(db.String(50), nullable=False)
    filename = db.Column(db.String(200), nullable=False)


with app.app_context():
    db.create_all()

    gallery_folder = os.path.join(app.root_path, 'static', 'images', 'gallery')
    os.makedirs(gallery_folder, exist_ok=True)

    if not Performance.query.first():
        sample_events = [
            Performance(title="UC Intramurals Opening Ceremony", date="September 18, 2026", location="UC Main Campus Gym"),
            Performance(title="Sinulog Grand Parade Performance", date="January 17, 2027", location="Cebu City")
        ]
        db.session.bulk_save_objects(sample_events)
        db.session.commit()

    if not GalleryPhoto.query.first():
        seed_photos = [
            GalleryPhoto(title="Tabo sa UC PRI", year="2025", category="Events", filename="uctabo.png"),
            GalleryPhoto(title="Philippine Independence Day", year="2026", category="Parades", filename="uc2026.png"),
            GalleryPhoto(title="Intramurals", year="2026", category="Intramurals", filename="ucgroup.png"),
        ]
        db.session.bulk_save_objects(seed_photos)
        db.session.commit()


@app.route('/')
def home():
    upcoming_events = Performance.query.all()
    latest_photos = GalleryPhoto.query.order_by(GalleryPhoto.id.desc()).limit(3).all()
    return render_template('index.html', events=upcoming_events, latest_photos=latest_photos)


@app.route('/history')
def history():
    return render_template('history.html')


@app.route('/login', methods=['GET', 'POST'])
def login():
    error = None
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '').strip()
        if username == ADMIN_USERNAME and password == ADMIN_PASSWORD:
            session['is_admin'] = True
            return redirect(url_for('gallery'))
        else:
            error = 'Incorrect username or password.'
    return render_template('login.html', error=error)


@app.route('/logout')
def logout():
    session.pop('is_admin', None)
    return redirect(url_for('gallery'))


@app.route('/gallery', methods=['GET', 'POST'])
def gallery():
    if request.method == 'POST':
        if not session.get('is_admin'):
            return redirect(url_for('login'))

        file = request.files.get('photo')
        title = request.form.get('title', '').strip()
        year = request.form.get('year', '').strip()
        category = request.form.get('category', '').strip()

        if file and title and year and category and allowed_file(file.filename):
            ext = file.filename.rsplit('.', 1)[1].lower()
            filename = f"{uuid.uuid4().hex}.{ext}"
            upload_folder = os.path.join(app.root_path, 'static', 'images', 'gallery')
            file.save(os.path.join(upload_folder, filename))

            new_photo = GalleryPhoto(
                title=title, year=year, category=category,
                filename=f"gallery/{filename}"
            )
            db.session.add(new_photo)
            db.session.commit()

        return redirect(url_for('gallery'))

    photos = GalleryPhoto.query.order_by(GalleryPhoto.year.desc(), GalleryPhoto.id.desc()).all()
    categories = sorted(set(p.category for p in photos))
    years = sorted(set(p.year for p in photos), reverse=True)
    is_admin = session.get('is_admin', False)
    return render_template('gallery.html', photos=photos, categories=categories, years=years, is_admin=is_admin)


@app.route('/roster', methods=['GET', 'POST'])
def roster():
    if request.method == 'POST':
        member_name = request.form.get('name')
        member_section = request.form.get('section')
        member_instrument = request.form.get('instrument')

        if member_name and member_section and member_instrument:
            new_member = Member(name=member_name, section=member_section, instrument=member_instrument)
            db.session.add(new_member)
            db.session.commit()

        return redirect(url_for('roster'))

    all_members = Member.query.all()
    return render_template('roster.html', members=all_members)


if __name__ == '__main__':
    app.run(debug=True)
