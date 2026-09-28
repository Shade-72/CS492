from django.urls import path

from . import views

app_name = "family_portal"

urlpatterns = [
    path("parent/children/", views.children_page, name="children"),
    path("parent/children/<str:student_id>/", views.child_records_page, name="child_records"),
    path("api/parent/children/", views.api_children, name="api_children"),
    path("api/parent/children/<str:student_id>/records/", views.api_child_records, name="api_child_records"),
    path("messages/", views.inbox_page, name="inbox"),
    path("messages/send/", views.send_message, name="send_message"),
    path("messages/<int:thread_id>/", views.thread_page, name="thread"),
    path("api/messages/", views.api_inbox, name="api_inbox"),
    path("api/messages/send/", views.api_send, name="api_send"),
    path("api/messages/<int:thread_id>/", views.api_thread, name="api_thread"),
    path("api/messages/<int:thread_id>/reply/", views.api_reply, name="api_reply"),
]
