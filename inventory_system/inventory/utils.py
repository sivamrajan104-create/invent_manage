def is_admin(user):
    return user.is_superuser

def is_staff(user):
    return user.groups.filter(name="Staff").exists()
