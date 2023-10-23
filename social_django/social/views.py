from django.shortcuts import render,redirect,get_object_or_404
from django.urls import reverse
from . models import*
from .forms import UserRegisterForm,PostForm, UserProfileForm
from django.contrib.auth.forms import UserCreationForm
from django.contrib import messages
from django.contrib.auth.models import User
from .forms import EditProfileForm
from django.contrib.auth.decorators import login_required
from django.contrib.auth.views import LoginView
from django.contrib.auth.views import PasswordResetView
from azure.core.credentials import AzureKeyCredential
from azure.ai.textanalytics import TextAnalyticsClient




# Create your views here.
from django.contrib.auth.views import LoginView

def inicio_sesion(request):
    if request.user.is_authenticated:
        return redirect('perfil')  # Redirigir a la página de perfil si el usuario ya está autenticado
    return LoginView.as_view(template_name='social/login.html')(request)
@login_required
def feed(request):
    posts = Post.objects.all()

    for post in posts:
        post.user_liked = post.likes.filter(id=request.user.id).exists()

    context = {'posts': posts}
    return render(request, 'social/feed.html', context)


def register(request):
    if request.method=='POST':
        form =UserRegisterForm(request.POST)
        profile_form = UserProfileForm(request.POST, request.FILES)
        if form.is_valid() and profile_form.is_valid():
            user = form.save()
            profile = profile_form.save(commit=False)
            profile.user = user
            profile.save()
            username=form.cleaned_data['username']
            messages.success(request, f'Bienvenido a ARTIX {username}')
            return redirect('login')

    else:
        form=UserRegisterForm()
        profile_form = UserProfileForm()
    context={'form':form, 'profile_form': profile_form}
    return render(request,'social/register.html',context)


@login_required
def profile(request, username=None):
    current_user = request.user
    if username and username != current_user.username:
        user = User.objects.get(username=username)
        posts = user.posts.all()
    else:
        posts = current_user.posts.all()
        user = current_user

    user_type = None
    if hasattr(current_user.extendeddata, 'user_type'):
        user_type = current_user.extendeddata.user_type

    return render(request, 'social/profile.html', {'user': user, 'posts': posts, 'user_type': user_type})


@login_required
def post(request):
    # Obtiene el usuario actual
    current_user = get_object_or_404(User, pk=request.user.pk)
    result = None  # Inicializa result como una lista vacía
    if request.method == 'POST':
        # Si el método de la solicitud es POST, procesa el formulario
        form = PostForm(request.POST, request.FILES)
        if form.is_valid():
            # Si el formulario es válido, guarda el post asociándolo al usuario actual
            post = form.save(commit=False)
            post.user = current_user
            post.save()

            # API key_phrases
            credential = AzureKeyCredential("fad32181f2334484892d89722c6d7761")
            endpoint = "https://lenguajedscrscl.cognitiveservices.azure.com/"

            text_analytics_client = TextAnalyticsClient(endpoint, credential)
            documents = [post.content]
            response = text_analytics_client.extract_key_phrases(documents, language="es")

            for doc in response:
                if not doc.is_error:
                    result = doc.key_phrases  # Asigna las palabras clave a result
                    post.key_result = ', '.join(result)  # Actualiza el campo key_result del post
                    post.save()  # Guarda el post nuevamente con las palabras clave
            # Agregar impresión de depuración
            print("Resultado de palabras clave:", result)
            messages.success(request, 'Post publicado correctamente')
            return redirect('feed')
    else:
        # Si la solicitud no es POST, crea un formulario en blanco
        form = PostForm()

    # Renderiza la plantilla 'social/post.html' con el formulario
    return render(request, 'social/post.html', {'form': form, 'result': result})

#Vista para el follow y unfollow
@login_required
def follow(request,username):
    current_user=request.user
    to_user=User.objects.get(username=username)
    to_user_id=to_user
    rel=Relationship(from_user=current_user,to_user=to_user_id)
    rel.save()
    messages.success(request,f'Sigues a {username}')
    return redirect('feed')

@login_required
def unfollow(request,username):
    current_user=request.user
    to_user=User.objects.get(username=username)
    to_user_id=to_user.id
    try:
        rel=Relationship.objects.filter(from_user=current_user.id,to_user=to_user_id).get()
        rel.delete()
        messages.success(request,f'Dejaste de seguir a {username}')
    except Relationship.DoesNotExist:
        messages.error(request, f'No estás siguiendo a {username}')
    return redirect(reverse('profile', args=[current_user.username]))

@login_required
def followers(request, username):
    user = get_object_or_404(User, username=username)
    return render(request, 'social/followers.html', {'followers': user.profile.get_followers()})

@login_required
def following(request, username):
    user = get_object_or_404(User, username=username)
    return render(request, 'social/following.html', {'following': user.profile.get_following()})

@login_required
def add_to_favorites(request, post_id):
    try:
        post = Post.objects.get(id=post_id)
    except Post.DoesNotExist:
        pass
    request.user.profile.favorites.add(post)
    return redirect('feed') 
def remove_from_favorites(request, post_id):
    if request.method == 'POST':
        try:
            post = Post.objects.get(id=post_id)
            request.user.profile.favorites.remove(post)
            messages.success(request, f'Has eliminado la obra de tus descubrimientos')
        except Post.DoesNotExist:
            pass
    return redirect('favorites')


@login_required
def deleteproduct (request, post_id):
    post = Post.objects.get(pk = post_id) 
    data_context={'post':post}
    if request.method == 'POST':
        print(request.POST)
        if 'yes' in request.POST:
            post.deleted_date=timezone.now()
            post.save()
            return redirect ('home')
    return render(request,'delete_product.html',data_context)

@login_required
def edit_post(request, post_id):
    post = get_object_or_404(Post, id=post_id)

    if request.method == 'POST':
        form = PostForm(request.POST, request.FILES, instance=post)
        if form.is_valid():
            form.save()
            # API key_phrases
            credential = AzureKeyCredential("fad32181f2334484892d89722c6d7761")
            endpoint = "https://lenguajedscrscl.cognitiveservices.azure.com/"

            text_analytics_client = TextAnalyticsClient(endpoint, credential)
            documents = [post.content]
            response = text_analytics_client.extract_key_phrases(documents, language="es")

            for doc in response:
                if not doc.is_error:
                    result = doc.key_phrases  # Asigna las palabras clave a result
                    post.key_result = ', '.join(result)  # Actualiza el campo key_result del post
                    post.save()  # Guarda el post nuevamente con las palabras clave
            # Agregar impresión de depuración
            messages.success(request, 'Cambios guardados correctamente')
            return redirect('feed')
    else:
        form = PostForm(instance=post)

    return render(request, 'social/edit_post.html', {'form': form, 'post': post})

@login_required
def delete_post(request, post_id):
    post = get_object_or_404(Post, id=post_id)

    if request.method == 'POST':
        post.delete()
        messages.success(request, 'Post eliminado correctamente')
        return redirect('feed')

    return render(request, 'social/delete_post.html', {'post': post})
def post_details(request, post_id):
    post = get_object_or_404(Post, id=post_id)
    likes = post.likes.all()

    context = {'post': post, 'likes': likes}
    return render(request, 'social/post_details.html', context)

@login_required
def like_post(request, post_id):
    post = get_object_or_404(Post, id=post_id)
    post.likes.add(request.user)
    request.user.profile.favorites.add(post)  # Agrega el post a los favoritos del usuario
    messages.success(request, 'Te gusta esta obra')
    return redirect('feed')

@login_required
def unlike_post(request, post_id):
    post = get_object_or_404(Post, id=post_id)
    post.likes.remove(request.user)
    request.user.profile.favorites.remove(post)  # Remover el post de los favoritos del usuario
    messages.success(request, 'Te dejo de gustar esta obra')
    return redirect('feed')



@login_required
def likes_list(request, post_id):
    post = get_object_or_404(Post, id=post_id)
    likes = post.likes.all()
    return render(request, 'social/likes_list.html', {'post': post, 'likes': likes})

@login_required
def favorites(request):
    if request.user.is_authenticated:
        try:
            favorites = request.user.profile.favorites.all()
            liked_posts = request.user.extendeddata.liked_posts.all()  # Recupera los posts que el sponsor ha marcado como favoritos
            context = {'favorites': favorites, 'liked_posts': liked_posts}
            return render(request, 'social/favorites.html', context)
        except AttributeError:
            return render(request, 'social/favorites.html', {'message': 'El perfil del usuario no está configurado correctamente.'})
    else:
        return render(request, 'social/favorites.html', {'message': 'Debes iniciar sesión para ver tus favoritos.'})

def add_to_favorites(request, post_id):
    try:
        post = Post.objects.get(id=post_id)
        request.user.profile.favorites.add(post)
        post.likes.add(request.user)  # Añadir el usuario a los likes del post
        messages.success(request, 'Obra añadida a tus descubrimientos correctamente')
    except Post.DoesNotExist:
        messages.error(request, 'Esta obra no existe')
    return redirect('feed')

@login_required
def favorites(request):
    if request.user.is_authenticated and request.user.extendeddata.user_type == 'S':
        favorites = request.user.profile.favorites.all()
        return render(request, 'social/favorites.html', {'favorites': favorites})
    else:
        return render(request, 'social/favorites.html', {'message': 'Debes iniciar sesión como sponsor para ver tus favoritos.'})
    
@login_required
def edit_profile(request):
    if request.method == 'POST':
        user_form = EditProfileForm(request.POST, instance=request.user)
        if user_form.is_valid():
            user = user_form.save(commit=False)
            user.save()

            profile = request.user.profile
            profile.description = user_form.cleaned_data['description']
            
            # Verifica si se ha proporcionado una nueva imagen
            if 'image' in request.FILES:
                profile.image = request.FILES['image']
            
            profile.save()

            return redirect('profile')
    else:
        user_form = EditProfileForm(instance=request.user)
    
    return render(request, 'social/edit_profile.html', {'user_form': user_form})







