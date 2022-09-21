from django.core.paginator import Paginator

COUNT_PAGE: int = 10


def get_paginated_post(request, post_list):
    pag = Paginator(post_list, COUNT_PAGE)
    page_number = request.GET.get('page')
    page_object = pag.get_page(page_number)
    return page_object
