from django.shortcuts import render, redirect, get_object_or_404
from django.http import JsonResponse, HttpResponse
from django.urls import reverse
from blog.util import paginate
from blog.models import Privacy, Post
from users.models import Author, Node
from users import models
from django.contrib import auth
from django.views.decorators.http import require_POST
from django.views.decorators.csrf import csrf_exempt
from django.core.exceptions import ObjectDoesNotExist
import blog
import json
import base64
import datetime
import requests



def http_basic_authenticate(request):
    if 'Authorization' not in request.headers:
        return None

    hval = request.headers['Authorization']
    if not hval.startswith("Basic "):
        return None

    username, password = base64.b64decode(hval[len("Basic "):].encode("ascii"))\
                               .decode("utf-8").split(":")
    return auth.authenticate(request, username=username,
                             password=password)

def auth_api(func):
    def inner(request, *args, **kwargs):
        #TODO: authenticate with HTTP basic auth
        user = http_basic_authenticate(request)
        if user is not None:
            auth.login(request, user)

        return func(request, *args, **kwargs)

    return inner

def render_posts(request, postlist, urlbase):
    page = int(request.GET.get("page", 0))
    size = int(request.GET.get("size", DEFAULT_PAGE_SIZE))

    total = len(postlist)

    def pageurl(n):
        return "{}?page={}&size={}".format(
            urlbase, n, size)

    nex = {"next": pageurl(page+1) } if (page+1)*size < total else {}
    prev = {"previous": pageurl(page-1) } if page > 0 else {}

    posts = list(paginate(postlist, page, size))
    return JsonResponse({
        "query": "posts",
        "count": total,
        "size": size,
        **nex,
        **prev,
        "posts": [serialize_post(request, p) for p in posts]
    })

@auth_api
def author_posts(request):
    return render_posts(
        request,
        [p for p in blog.models.Post.objects.all().order_by("-pk")
         if p.listable_to(request.user)],
        api_reverse(request, "api_posts")
    )

DEFAULT_PAGE_SIZE = 25

def api_reverse(request, path, **kwargs):
    return request.build_absolute_uri(reverse(path, kwargs=kwargs))


def serialize_author(request, author):
    return {
        "id": api_reverse(request, "api_author",
                          author_id=author.pk),
        "host": api_reverse(request, "api_root"),
        "displayName": author.user.username,
        "url": api_reverse(request, "api_author",
                           author_id=author.pk),
        "github": author.github and "https://github.com/"+author.github
    }

def serialize_post(request, post):
    visibility_table = {
        Privacy.PRIVATE: "PRIVATE",
        Privacy.URL_ONLY: "PUBLIC",
        Privacy.FRIENDS: "FRIENDS",
        Privacy.FOAF: "FOAF",
        Privacy.PUBLIC: "PUBLIC",
    }
    return {
        "title": post.title,
        "source": api_reverse(request, "api_post", post_id=post.pk),
        "origin": api_reverse(request, "api_post", post_id=post.pk),
        "description": None, #TODO
        "contentType": post.content_type,
        "content": post.content, #TODO: images
        "author": serialize_author(request, post.author),

        #TODO: comment pagination
        "count": len(post.comments.all()),
        "size": DEFAULT_PAGE_SIZE,
        "next": api_reverse(request, "api_post_comments", post_id=post.pk),
        "comments": [serialize_comment(request, c)
                     for c in paginate(post.comments.all(), 0, 5)],

        "published": post.date,
        "id": post.pk,
        "visibility": visibility_table[post.privacy],
        "visibleTo": None,
        "unlisted": post.privacy == Privacy.URL_ONLY
    }

def serialize_comment(request, comment):
    if comment.author is not None:
        author = serialize_author(request, comment.author)
    else:
        authentication = models.Node.URItoAuth(comment.rauthor.url)
        author_json = requests.get(comment.rauthor.url, headers=authentication).json()
        author = {
            "id": comment.rauthor.url,
            "host": author_json["host"],
            "displayName": author_json["displayName"],
        }

    return {
        "author": author,
        "comment": comment.comment,
        "contentType": "text/plain",
        "published": comment.date,
        "id": str(comment.pk),
    }

@csrf_exempt
@auth_api
def posts(request):
    if request.method == "POST":
        visibility_table = {
            "PRIVATE": Privacy.PRIVATE,
            #"PUBLIC": Privacy.URL_ONLY,
            "FRIENDS": Privacy.FRIENDS,
            "FOAF": Privacy.FOAF,
            "PUBLIC": Privacy.PUBLIC,
        }
        author = Author.from_user(request.user)
        if author is None:
            return JsonResponse({}, status=401)

        try:
            data = json.loads(request.body)
            title   = data["title"]
            content = data["content"]
            content_type = data["contentType"]
            privacy = data["visibility"] if "visibility" in data else "PUBLIC"
            privacy = visibility_table[privacy]
            if "unlisted" in data and data["unlisted"]:
                privacy = Privacy.URL_ONLY
        except (json.decoder.JSONDecodeError, KeyError):
            return JsonResponse({}, status=400)


        post = Post.objects.create(date=datetime.date.today(),
                                   title=title,
                                   content=content,
                                   author=author,
                                   content_type=content_type,
                                   image=None, #TODO
                                   privacy=privacy)

        return redirect("api_post", post.pk)
    else:
        return render_posts(
            request,
            blog.models.Post.public(),
            api_reverse(request, "api_posts")
        )


@auth_api
def authorid_posts(request, author_id):
    author = get_object_or_404(Author, pk=author_id)
    return render_posts(
        request,
        [p for p in author.posts.order_by("-pk")
         if p.listable_to(request.user)],
        api_reverse(request, "api_authoridposts", author_id=author_id),
    )


@csrf_exempt
@auth_api
def post(request, post_id):
    post = get_object_or_404(Post, pk=post_id)

    if request.method == "PUT":
        visibility_table = {
            "PRIVATE": Privacy.PRIVATE,
            #"PUBLIC": Privacy.URL_ONLY,
            "FRIENDS": Privacy.FRIENDS,
            "FOAF": Privacy.FOAF,
            "PUBLIC": Privacy.PUBLIC,
        }
        author = Author.from_user(request.user)
        if author is None or author != post.author:
            return JsonResponse({}, status=401)

        try:
            data = json.loads(request.body)
        except json.decoder.JSONDecodeError:
            return JsonResponse({}, status=400)

        if "title" in data:
            post.title   = data["title"]
        if "content" in data:
            post.content = data["content"]
        if "contentType" in data:
            post.content_type = data["contentType"]
        if "visibility" in data:
            try:
                post.privacy = visibility_table[data["visibility"]]
            except KeyError:
                return JsonResponse({}, status=400)
        if "unlisted" in data and data["unlisted"]:
            post.privacy = Privacy.URL_ONLY

        post.save()

    return JsonResponse(serialize_post(request, post))


@csrf_exempt
@auth_api
def post_comments(request, post_id):
    post = get_object_or_404(Post, pk=post_id)

    if request.method == "POST":
        data = json.loads(request.body)
        aid = data["comment"]["author"]["id"]
        if aid.startswith(request_host(request)):
            author = models.Author.objects.get(
                pk=int(aid.split("/")[-1]))
        else:
            try:
                author = models.extAuthor.objects.get(url=aid)
            except ObjectDoesNotExist:
                author = models.extAuthor.objects.create(url=aid)

        post.comment(author, data["comment"]["comment"])
        return JsonResponse({
            "query": "addComment",
            "success": True,
            "message": "Comment Added"
        })
    else:
        comments = [serialize_comment(request, c) for c in post.comments.all()]
        page = int(request.GET.get("page", 0))
        size = int(request.GET.get("size", DEFAULT_PAGE_SIZE))

        total = len(comments)

        def pageurl(n):
            return "{}?page={}&size={}".format(
                urlbase, n, size)

        nex = {"next": pageurl(page+1) } if (page+1)*size < total else {}
        prev = {"previous": pageurl(page-1) } if page > 0 else {}

        comments = list(paginate(comments, page, size))
        return JsonResponse({
            "query": "comments",
            "count": total,
            "size": size,
            **nex,
            **prev,
            "comments": comments
        })


@csrf_exempt
@auth_api
def author_friends(request, author_id):
    author = get_object_or_404(Author, pk=author_id)
    if request.method == "POST":
        try:
            data = json.loads(request.body)
            friends = set(data["authors"])
            #the spec also adds a extraneous "author" field
        except (json.decoder.JSONDecodeError, KeyError):
            return JsonResponse({}, status=400)

        return JsonResponse({
            "query": "friends",
            "author": api_reverse(request, "api_author",
                                  author_id=author.pk),
            "authors": [
                api_reverse(request, "api_author",
                            author_id=a.pk)
                for a in author.get_friends()
                if api_reverse(request, "api_author",
                               author_id=a.pk)
                in friends
            ],
        })
    else:
        return JsonResponse({
            "query": "friends",
            "authors": [
                api_reverse(request, "api_author",
                            author_id=a.pk)
                for a in author.get_friends()
            ],
        })


@auth_api
def author_friendswith(request, author_id, author_id2):
    author1 = get_object_or_404(Author, pk=author_id)
    author2 = get_object_or_404(Author, pk=author_id2)

    return JsonResponse({
        "query": "friends",
        "authors": [
            api_reverse(request, "api_author", author_id=author1.pk),
            api_reverse(request, "api_author", author_id=author2.pk),
        ],
        "friends": author1.friends_with(author2)
    })


def request_host(request):
    return request.build_absolute_uri(reverse("api_root"))

def author_from_url(host, id):
    if id.startswith(host):
        author_id = int(id.split('/')[-1])
        return get_object_or_404(Author, pk=author_id)
    else:
        author_id = int(id.split('/')[-1])
        assert False



def local_local_friendrequest(host, data):
    author_id = int(data["author"]["id"].split('/')[-1])
    author = get_object_or_404(Author, pk=author_id)
    fiend_id = int(data["friend"]["id"].split('/')[-1])
    friend = get_object_or_404(Author, pk=fiend_id)
    author.follow(friend)

def local_remote_friendrequest(host, data):
    author_id = int(data["author"]["id"].split('/')[-1])
    author = get_object_or_404(Author, pk=author_id)
    try:
        models.extAuthor.objects.get(url = data["friend"]["id"])
    except ObjectDoesNotExist:
        models.extAuthor.objects.create(url = data["friend"]['id'])
    ext_friend = models.extAuthor.objects.get(url = data["friend"]['id'])
    author.follow_ext(ext_friend)

def remote_local_friendrequest(host, data):
    try:
        models.extAuthor.objects.get(url = data["author"]["id"])
    except ObjectDoesNotExist:
        models.extAuthor.objects.create(url = data["author"]['id'])
    ext_author = models.extAuthor.objects.get(url = data["author"]['id'])
    friend_id = int(data["friend"]["id"].split('/')[-1])
    friend = get_object_or_404(Author, pk=friend_id)
    friend.follow_by_ext(ext_author)

    '''
    # ----- friend request format -----
    you_json = serialize_author(request,you)
    friend_request = {}
    friend_request["query"] = "friendrequest"
    friend_request["author"] = you_json
    friend_request["friend"] = author_json
    # ----- friend request format -----
    target_url = author_json['host']+'friendrequest'
    requests.post( target_url, data=friend_request)
    '''



@csrf_exempt
@auth_api
@require_POST
def friendrequest(request):
    '''
        This function is to let author follow friend,
        there are 3 different cases:
        author is a local user and friend is a local user
        author is a local user and friend is a remote user
        author is a remote user and friend is a local user
    '''
    data = json.loads(request.body)
    host = request_host(request)
    try:
        author_id = data["author"]["id"]
        friend_id = data["friend"]["id"]
        if author_id.startswith(host) and friend_id.startswith(host):
            local_local_friendrequest(host, data)
        elif author_id.startswith(host) and not friend_id.startswith(host):
            local_remote_friendrequest(host, data)
        elif not author_id.startswith(host) and friend_id.startswith(host):
            remote_local_friendrequest(host, data)
        else:
            # Our server does not handle the relationship between remote user and remote user
            raise NameError
    except KeyError:
        return JsonResponse({}, status=404)
    except NameError:
        return JsonResponse({}, status=400)
    return JsonResponse({})


@auth_api
def author(request, author_id):
    author = get_object_or_404(Author, pk=author_id)
    return JsonResponse({
        **serialize_author(request, author),
        "friends": [serialize_author(request, f)
                    for f in author.get_friends()]
    })
