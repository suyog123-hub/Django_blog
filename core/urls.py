from django.urls import path

from . import views

urlpatterns = [
    path("", views.homePage, name="home"),
    path("blogs/", views.blogsPage, name="blogs"),
    path("register/", views.registerPage, name="register"),
    path("login/", views.loginPage, name="login"),
    path("logout/", views.logoutUser, name="logout"),
    path("add_blog/", views.addBlogPage, name="addBlog"),
    path("my_blogs/", views.myBlogsPage, name="myBlogs"),
    path("edit_blog/<int:id>/", views.editBlogPage, name="editBlog"),
    path("delete_blog/<int:id>/", views.deleteBlog, name="deleteBlog"),
    path("pending/", views.pendingBlogsPage, name="pending"),
    path("approve_blog/<int:id>/", views.approveBlog, name="approveBlog"),
    path("profile/", views.profilePage, name="profile"),
]
