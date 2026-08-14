# MyBlog - Django Blogging Platform

A simple and clean blogging platform built with Django where anyone can create an account, write a blog post, and get it published after admin approval.

**Live Demo:** [https://suyogblog.onrender.com/](https://django-blog-7lqy.onrender.com/)

## Features

- User registration, login, and logout
- Create blog posts with a title, content, and optional cover image
- Admin approval workflow - blogs are published only after admin approval
- "My Blogs" section to view, edit, and manage your own posts
- Only the author can edit their own blog
- Admin panel to review and approve pending blogs
- Responsive design (Bootstrap-based templates)

## Tech Stack

- **Backend:** Django 6.0
- **Database:** SQLite (development) / PostgreSQL (production)
- **Frontend:** HTML, CSS, Bootstrap
- **Environment:** python-decouple for config management
- **Deployment:** Render

## Getting Started

### Prerequisites

- Python 3.12+
- pip

### Installation

1. Clone the repository:

   ```bash
   git clone https://github.com/suyog123-hub/Django_blog.git
   cd Django_blog
   ```

2. Create and activate a virtual environment:

   ```bash
   python -m venv myenv
   source myenv/bin/activate   # On Windows: myenv\Scripts\activate
   ```

3. Install dependencies:

   ```bash
   pip install -r requirements.txt
   ```

4. Create a `.env` file in the project root with your settings:

   ```env
   SECRET_KEY=your-secret-key-here
   DEBUG=True
   ```

   > Generate a secret key with:
   > `python -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"`

5. Run migrations:

   ```bash
   python manage.py migrate
   ```

6. Create a superuser (admin):

   ```bash
   python manage.py createsuperuser
   ```

7. Start the development server:

   ```bash
   python manage.py runserver
   ```

8. Visit `http://127.0.0.1:8000/` in your browser.

## Usage

- **Readers:** Browse published blogs without an account.
- **Writers:** Register, log in, and submit blog posts. Your post goes live once approved by an admin.
- **Admin:** Log in as a superuser and go to `/pending/` to approve or delete submitted blogs. The Django admin (`/admin/`) is also available.

## Project Structure

```
blog/
├── blog/               # Project configuration (settings, urls, wsgi)
├── core/               # Main app (models, views, urls, templates, static)
│   ├── models.py       # Blog model
│   ├── views.py        # View functions
│   ├── urls.py         # App URLs
│   ├── templates/      # HTML templates
│   └── static/         # CSS and images
├── blogs/              # Uploaded blog cover images
├── manage.py
└── requirements.txt
```

## Environment Variables

| Variable       | Description                        | Default |
| -------------- | ---------------------------------- | ------- |
| `SECRET_KEY`   | Django secret key                  | `django-insecure-dev-only-key` |
| `DEBUG`        | Set to `False` in production       | `True`  |

## Deployment on Render

1. Push the code to GitHub.
2. Create a new **Web Service** on [Render](https://render.com) and connect the repository.
3. Set the build command:

   ```bash
   pip install -r requirements.txt
   ```

4. Set the start command:

   ```bash
   gunicorn blog.wsgi
   ```

5. Add environment variables in the Render dashboard: `SECRET_KEY` and `DEBUG=False`.
6. Deploy. The app will be available at the URL Render provides.

## License

This project is for educational/demo purposes.
