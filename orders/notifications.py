from django.conf import settings
from accounts.task_notifications import send_whatsapp_task


def _format_order_status_message(order, status):
    if status == order.Status.PLACED:
        return (
            f"Your order #{order.id} has been placed successfully! "
            f"Total: ₹{order.grand_total:.2f}. We will notify you when it is out for delivery."
        )

    if status == order.Status.CONFIRMED:
        return (
            f"Order #{order.id} is confirmed and assigned to {order.delivery_member.get_full_name() or order.delivery_member.mobile}. "
            "It will be delivered soon."
        )

    if status == order.Status.OUT_FOR_DELIVERY:
        return (
            f"Order #{order.id} is out for delivery with {order.delivery_member.get_full_name() or order.delivery_member.mobile}. "
            "You can track it from your order details page."
        )

    if status == order.Status.DELIVERED:
        return (
            f"Order #{order.id} has been delivered. Thank you for ordering with us!"
        )

    return f"Order #{order.id} status updated to {order.get_status_display()}."


def notify_customer(order, status):
    if not order.customer.mobile:
        return
    message = _format_order_status_message(order, status)
    if settings.CELERY_TASK_ALWAYS_EAGER:
        send_whatsapp_task.apply(args=[order.customer.mobile, message])
    else:
        send_whatsapp_task.delay(order.customer.mobile, message)


def notify_area_admin(order, status):
    if not order.area:
        return
    area_admins = order.area.staff.filter(role='area_admin')
    message = (
        f"Order #{order.id} status updated to {order.get_status_display()} for area {order.area.name}. "
        "Please review if any action is needed."
    )
    for admin in area_admins:
        if not admin.mobile:
            continue
        if settings.CELERY_TASK_ALWAYS_EAGER:
            send_whatsapp_task.apply(args=[admin.mobile, message])
        else:
            send_whatsapp_task.delay(admin.mobile, message)


def notify_delivery_member(order, status):
    if not order.delivery_member or not order.delivery_member.mobile:
        return
    if status == order.Status.PLACED:
        message = (
            f"New order #{order.id} has been placed in your area {order.area.name}. "
            "Please wait for assignment details."
        )
    elif status == order.Status.CONFIRMED:
        message = (
            f"Order #{order.id} has been assigned to you. "
            "Please pick it up and start delivery."
        )
    elif status == order.Status.OUT_FOR_DELIVERY:
        message = (
            f"Order #{order.id} is out for delivery. "
            "Please deliver it promptly."
        )
    elif status == order.Status.DELIVERED:
        message = f"Order #{order.id} has been marked delivered. Great work!"
    else:
        message = f"Order #{order.id} status changed to {order.get_status_display()}."

    if settings.CELERY_TASK_ALWAYS_EAGER:
        send_whatsapp_task.apply(args=[order.delivery_member.mobile, message])
    else:
        send_whatsapp_task.delay(order.delivery_member.mobile, message)
