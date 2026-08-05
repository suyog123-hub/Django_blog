from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.models import User

from .models import Blog

# If you have a Comment model, uncomment this:
# from .models import Blog, Comment


def homePage(request):
    return render(request, "crud_enotes/home.html")


def blogsPage(request):
    blogs = Blog.objects.filter(is_approved=True).order_by('-created_date')
    return render(request, "crud_enotes/blogs.html", {"blogs": blogs})


def registerPage(request):
    if request.method == "POST":
        username = request.POST["username"].strip()
        email = request.POST["email"].strip()
        password = request.POST["password"]
        confirm_password = request.POST["confirm_password"]

        if not username or not email or not password:
            messages.error(request, "All fields are required.")
        elif password != confirm_password:
            messages.error(request, "Passwords do not match.")
        elif User.objects.filter(username=username).exists():
            messages.error(request, "This username is already taken.")
        else:
            User.objects.create_user(username=username, email=email, password=password)
            messages.success(request, "Account created successfully. Please login.")
            return redirect("login")

    return render(request, "crud_enotes/register.html")


def loginPage(request):
    if request.method == "POST":
        username = request.POST["username"]
        password = request.POST["password"]
        user = authenticate(request, username=username, password=password)
        if user is not None:
            login(request, user)
            return redirect("home")
        messages.error(request, "Invalid username or password.")

    return render(request, "crud_enotes/login.html")


def logoutUser(request):
    logout(request)
    return redirect("home")


@login_required(login_url="login")
def profilePage(request):
    """
    Display user profile with statistics and recent posts.
    """
    user = request.user
    user_blogs = Blog.objects.filter(author=user).order_by('-created_date')
    
    # If you have a Comment model, count the user's comments:
    # user_comments = Comment.objects.filter(author=user).count()
    
    context = {
        "user": user,
        "total_blogs": user_blogs.count(),
        "total_comments": 0,  # Replace with user_comments if you have a Comment model
        "recent_blogs": user_blogs[:5],  # Show last 5 blogs
        "is_admin": user.is_staff,
    }
    return render(request, "crud_enotes/profile.html", context)


@login_required(login_url="login")
def addBlogPage(request):
    if request.method == "POST":
        title = request.POST["title"].strip()
        content = request.POST["content"].strip()
        image = request.FILES.get("image")

        if not title or not content:
            messages.error(request, "Both title and content are required.")
        else:
            Blog.objects.create(title=title, content=content, image=image, author=request.user)
            messages.success(request, "Blog submitted successfully. It will be shown after admin approval.")
            return redirect("myBlogs")

    return render(request, "crud_enotes/add_blog.html")


@login_required(login_url="login")
def myBlogsPage(request):
    blogs = Blog.objects.filter(author=request.user).order_by('-created_date')
    return render(request, "crud_enotes/my_blogs.html", {"blogs": blogs})


@login_required(login_url="login")
def editBlogPage(request, id):
    blog = get_object_or_404(Blog, id=id)

    if blog.author != request.user:
        messages.error(request, "You can only edit your own blog.")
        return redirect("myBlogs")

    if request.method == "POST":
        title = request.POST["title"].strip()
        content = request.POST["content"].strip()
        image = request.FILES.get("image")

        if not title or not content:
            messages.error(request, "Both title and content are required.")
        else:
            blog.title = title
            blog.content = content
            if image:
                blog.image = image
            blog.save()
            messages.success(request, "Blog updated successfully.")
            return redirect("myBlogs")

    return render(request, "crud_enotes/edit_blog.html", {"blog": blog})


def pendingBlogsPage(request):
    if not request.user.is_authenticated or not request.user.is_staff:
        messages.error(request, "Only admin can access this page.")
        return redirect("home")

    blogs = Blog.objects.filter(is_approved=False).order_by('-created_date')
    return render(request, "crud_enotes/pending.html", {"blogs": blogs})


def approveBlog(request, id):
    if not request.user.is_authenticated or not request.user.is_staff:
        messages.error(request, "Only admin can approve blogs.")
        return redirect("home")

    blog = get_object_or_404(Blog, id=id)
    blog.is_approved = True
    blog.save()
    messages.success(request, f"Blog \"{blog.title}\" approved and published.")
    return redirect("pending")


def deleteBlog(request, id):
    if not request.user.is_authenticated or not request.user.is_staff:
        messages.error(request, "Only admin can delete blogs.")
        return redirect("home")

    blog = get_object_or_404(Blog, id=id)
    blog.delete()
    messages.success(request, "Blog deleted successfully.")
    return redirect("pending")