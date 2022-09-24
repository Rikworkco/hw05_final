from django import forms
from . models import Post, Comment


class PostForm(forms.ModelForm):
    class Meta:
        model = Post
        fields = ('text', 'group', 'image')
        labels = {
            'group': ('Группа'),
            'text': ('Текст'),
        }
        help_texts = {
            'text': 'Текст нового поста',
            'group': 'Группа, к которой будет относиться пост',
        }


class CommentForm(forms.ModelForm):
    class Meta:
        model = Comment
        labels ={
            'text': ('Текст комментария')
        }
        fields = ['text']
        help_texts = {
            'text': 'Напишите комментарий'
        }
