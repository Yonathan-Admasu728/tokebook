import os
import django
from django.utils import timezone

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'tokebook.settings')
django.setup()

from django.contrib.auth import get_user_model
User = get_user_model()
from api.models import Casino

def create_test_data():
    print('Creating test users...')
    print('Use these credentials to log in:')
    print('--------------------------------')

    # Delete existing data
    User.objects.all().delete()
    Casino.objects.all().delete()
    print('\nCleared existing data')

    # Create super admin first
    admin = User.objects.create_superuser(
        username='admin',
        password='testpass123',
        email='admin@example.com',
        first_name='System',
        last_name='Administrator',
        role='ADMIN'
    )
    print('\nSuper Admin:')
    print(f'Username: admin, Password: testpass123')

    # Super admin creates the casino
    casino = Casino.objects.create(
        name='Test Casino'
    )
    print('\nCasino created by super admin')

    # Create casino managers (800000021-800000022)
    print('\nCasino Managers:')
    casino_managers = [
        ('William', 'Anderson'),
        ('Jennifer', 'Martinez')
    ]
    created_managers = []
    for i, (first_name, last_name) in enumerate(casino_managers, start=21):
        employee_id = f'800000{i:03d}'
        user = User.objects.create_user(
            username=employee_id,
            password='testpass123',
            email=f'{first_name.lower()}.{last_name.lower()}@example.com',
            first_name=first_name,
            last_name=last_name,
            role='CASINO_MANAGER',
            casino=casino.name,
            employee_id=employee_id,
            shift=i-20,  # 21->1, 22->2
            pencil_id=employee_id  # Set pencil_id for casino managers
        )
        created_managers.append(user)
        print(f'Username: {employee_id}, Name: {first_name} {last_name}')

    # Use first casino manager to create other roles
    active_manager = created_managers[0]

    # Create dealers (800000001-800000009)
    print('\nDealers:')
    dealers = [
        ('Michael', 'Johnson'),
        ('Sarah', 'Williams'),
        ('David', 'Brown'),
        ('Emily', 'Jones'),
        ('James', 'Davis'),
        ('Emma', 'Miller'),
        ('Daniel', 'Wilson'),
        ('Olivia', 'Moore'),
        ('Alexander', 'Taylor')
    ]
    for i, (first_name, last_name) in enumerate(dealers, start=1):
        employee_id = f'800000{i:03d}'
        User.objects.create_user(
            username=employee_id,
            password='testpass123',
            email=f'{first_name.lower()}.{last_name.lower()}@example.com',
            first_name=first_name,
            last_name=last_name,
            role='DEALER',
            casino=casino.name,
            employee_id=employee_id,
            shift=((i-1) // 3) + 1  # Assigns shifts 1, 1, 1, 2, 2, 2, 3, 3, 3
        )
        print(f'Username: {employee_id}, Name: {first_name} {last_name}')

    # Create supervisors (800000010-800000014)
    print('\nSupervisors:')
    supervisors = [
        ('Robert', 'Anderson'),
        ('Patricia', 'Thomas'),
        ('John', 'White'),
        ('Linda', 'Harris'),
        ('Richard', 'Clark')
    ]
    for i, (first_name, last_name) in enumerate(supervisors, start=10):
        employee_id = f'800000{i:03d}'
        User.objects.create_user(
            username=employee_id,
            password='testpass123',
            email=f'{first_name.lower()}.{last_name.lower()}@example.com',
            first_name=first_name,
            last_name=last_name,
            role='SUPERVISOR',
            casino=casino.name,
            employee_id=employee_id,
            shift=((i-10) // 2) + 1  # Assigns 2 supervisors per shift: 1,1,2,2,3,3
        )
        print(f'Username: {employee_id}, Name: {first_name} {last_name}')

    # Create pencils (800000015-800000018)
    print('\nPencils (Supervisors with pencil privileges):')
    pencils = [
        ('Christopher', 'Lee'),
        ('Barbara', 'Walker'),
        ('Joseph', 'Hall'),
        ('Margaret', 'Young')
    ]
    for i, (first_name, last_name) in enumerate(pencils, start=15):
        employee_id = f'800000{i:03d}'
        user = User.objects.create_user(
            username=employee_id,
            password='testpass123',
            email=f'{first_name.lower()}.{last_name.lower()}@example.com',
            first_name=first_name,
            last_name=last_name,
            role='SUPERVISOR',  # Pencils are supervisors with pencil privileges
            casino=casino.name,
            employee_id=employee_id,
            shift=((i-15) // 2) + 1  # Assigns shifts: 1,1,2,2
        )
        user.has_pencil_flag = True
        user.pencil_id = employee_id  # Set pencil_id for pencil supervisors
        user.save()
        print(f'Username: {employee_id}, Name: {first_name} {last_name}')

    # Create toke managers (800000019-800000020)
    print('\nToke Managers:')
    toke_managers = [
        ('Elizabeth', 'King'),
        ('Thomas', 'Wright')
    ]
    for i, (first_name, last_name) in enumerate(toke_managers, start=19):
        employee_id = f'800000{i:03d}'
        User.objects.create_user(
            username=employee_id,
            password='testpass123',
            email=f'{first_name.lower()}.{last_name.lower()}@example.com',
            first_name=first_name,
            last_name=last_name,
            role='TOKE_MANAGER',
            casino=casino.name,
            employee_id=employee_id,
            shift=i-18  # 19->1, 20->2
        )
        print(f'Username: {employee_id}, Name: {first_name} {last_name}')

    print('\nAll users created with password: testpass123')
    print('Test data created successfully!')

if __name__ == '__main__':
    create_test_data()
