from django.urls import path
from . import views


urlpatterns = [
    path('post',views.post,name='post'),
    path('post/<str:post_id>', views.viewpost, name='viewpost'),
    path('post/<int:post_id>/edit', views.edit, name='edit'),
    path('post/<int:post_id>/delete', views.delete, name='delete'),
    path('posts/all', views.allposts, name='allposts'),
    path('posts/friends', views.friends, name='friendposts'),
    path('post/<int:post_id>/comment', views.add_comment, name='addcomment'),
    path('post/<int:post_id>/<int:comment_id>/remove', views.remove_comment, name='removeComment'),
]
