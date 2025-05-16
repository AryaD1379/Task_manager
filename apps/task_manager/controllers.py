from py4web import action, request, abort, redirect, URL
from py4web.utils.form import Form, FormStyleBulma
from py4web.utils.url_signer import URLSigner
from .common import db, session, T, auth, logger, authenticated, unauthenticated, flash
from pydal.validators import *
from datetime import datetime
import copy

url_signer = URLSigner(session)

@action("index")
@action.uses("index.html", auth.user, db)
def index():
    tasks = db(db.task).select()
    return dict(tasks=tasks)

@action("task/create", method=["POST"])
@action.uses("task_form.html", auth.user, db)
def create_task():
    data = request.json
    data['created_by'] =  auth.user_id
    user = db(db.auth_user.id == auth.user_id).select(db.auth_user.first_name, db.auth_user.last_name).first()
    if user:
        created_by_name = user.first_name+" "+user.last_name
    else:
        created_by_name = ""
    data['created_by_name'] = created_by_name
    data_copy = copy.copy(data)
    print("data is")
    print(data)
    data_copy['deadline'] = datetime.strptime(data_copy['deadline'], '%Y-%m-%d')
    print(data_copy)
    resp = db.task.validate_and_insert(**data_copy)
    print(resp)
    return resp

@action("task/edit/<task_id:int>", method=["GET", "POST"])
@action.uses("task_form.html", auth.user, db)
def edit_task(task_id=None):
    task = db.task[task_id] or abort(404)
    if not can_edit_task(auth.user_id, task):
        abort(403)
    form = Form(db.task, record=task, deletable=False, csrf_session=session, formstyle=FormStyleBulma)
    if form.accepted:
        redirect(URL('index'))
    return dict(form=form)

@action("task/update", method=["POST"])
@action.uses("task_form.html", auth.user, db)
def update_task():
    data = request.json
    print("in update_task")
    print(data)
    if "assigned_to" in data:
        query = db(db.auth_user.id == data['assigned_to']).select(db.auth_user.first_name, db.auth_user.last_name).first()
        if query:
            assigned_to_name = query.first_name+" "+query.last_name
        else:
            assigned_to_name = ""
        data['assigned_to_name'] = assigned_to_name
        print("assigned_to_name")
        print(assigned_to_name)
    
    data_copy = copy.copy(data)
    print("data is")
    print(data)
    data_copy['deadline'] = datetime.strptime(data_copy['deadline'], '%Y-%m-%d')
    print(data_copy)

    resp = db.task.update_or_insert(db.task.id == data_copy['id'], **data_copy)
    print(resp)
    return resp


@action("task/comment/<taskid:int>", method=["POST"])
@action.uses(db, auth.user)
def comment(taskid=None):
    body = request.json.get('body')
    if not body:
        return dict(status='error', message='Comment body is required')
    
    db.comment.insert(taskid=taskid, body=body, author=auth.user_id)
    return dict(status='success')

@action("task/comments/<taskid:int>", method=["GET"])
@action.uses(db, auth.user)
def get_comments(taskid=None):
    comments = db(db.comment.taskid == taskid).select(db.comment.ALL, db.auth_user.ALL, left=db.auth_user.on(db.comment.author == db.auth_user.id))
    comments_list = []
    for comment in comments:
        comments_list.append({
            'id': comment.comment.id,
            'body': comment.comment.body,
            'post_date': comment.comment.post_date,
            'author': {
                'first_name': comment.auth_user.first_name,
                'last_name': comment.auth_user.last_name
            }
        })
    return dict(comments=comments_list)

@action("tasks", method=["GET"])
@action.uses(db, auth.user)
def get_tasks():
    user_id = auth.user_id
    query = (db.task.id > 0)
    date_created = request.params.get('date_created')
    deadline = request.params.get('deadline')
    status = request.params.get('status')
    created_by_self = request.params.get('created_by_self')
    assigned_to_self = request.params.get('assigned_to_self')
    created_by_managed_users = request.params.get('created_by_managed_users')
    assigned_to_managed_users = request.params.get('assigned_to_managed_users')
    created_by_user = request.params.get('created_by_user')
    assigned_to_user = request.params.get('assigned_to_user')   
   
    # Filter params
    # Should be a way to apply filters in a more elegant way
    if created_by_self == 'true':
        query &= (db.task.created_by == user_id)
    if assigned_to_self == 'true':
        query &= (db.task.assigned_to == user_id)
    if created_by_managed_users == 'true':
        managed_users = get_all_managed_users()
        print("managed_users: ", managed_users )
        query &= (db.task.created_by.belongs(managed_users))
    if assigned_to_managed_users == 'true':
        managed_users = get_all_managed_users()
        print("all_managed_users: ", managed_users )
        query &= (db.task.assigned_to.belongs(managed_users))
    if created_by_user:
        print("created_by_user: ", created_by_user)
        query &= (db.task.created_by_name == str(created_by_user))
    if assigned_to_user:
        print("assigned_to_user: ", assigned_to_user)
        query &= (db.task.assigned_to_name == (str(assigned_to_user)))
    
    if status:
        if (status != 'all'):
            query &= (db.task.status == status)
    
    # Sortings
    if date_created:
        orderby = ~db.task.date_created if date_created == 'true' else db.task.date_created
        tasks = db(query).select(orderby=orderby)
    if deadline:
        orderby = ~db.task.deadline if deadline == 'true' else db.task.deadline
        tasks = db(query).select(orderby=orderby)
    else:
        tasks = db(query).select()
    print("get_tasks")
    print(tasks)

    return dict(tasks=tasks.as_list())

@action("user/set_manager", method=["POST"])
@action.uses(db, auth.user)
def set_manager():
    user_id = request.json.get('user_id')
    manager_id = request.json.get('manager_id')
    if (not manager_id):
        manager_id = "None"


    print("set_manager")
    print(user_id)
    print(manager_id)
    # if user_id and manager_id:
    #     db.user_manager.update_or_insert(
    #         (db.user_manager.user_id == user_id),
    #         user_id=user_id,
    #         manager_id=manager_id
    #     )
    #     return dict(status='success')
    # return dict(status='error')
    try:
        assign_manager(user_id, manager_id)
        return dict(status="success")
    except ValueError as e:
        return dict(status="error", message=str(e))


@action("user/current_manager", method=["GET"])
@action.uses(db, auth.user)
def get_manager():
    # Fetch the manager_id associated with the current user
    rows = db(db.user_manager.user_id == auth.user_id).select(db.user_manager.manager_id)
    print("get_manager")

    # Initialize manager_id as None to handle cases where no manager is found
    manager_id = None

    if rows:
        manager_id = rows.first().manager_id

    print("Manager ID:", manager_id)

    # Fetch manager details if a manager_id was found
    if manager_id:
        manager = db(db.auth_user.id == manager_id).select(db.auth_user.first_name, db.auth_user.last_name).first()
        if manager:
            manager = manager.as_dict()
            manager["id"] = manager_id
        else:
            manager = {}
    else:
        manager = {}
    
    print("Manager Details:", manager)
    return manager

@action("user/get_manager/<user_id>", method=["GET"])
@action.uses(db, auth.user)
def get_user_manager(user_id):
    user_manager = db(db.user_manager.user_id == user_id).select(db.user_manager.manager_id).first()
    if user_manager:
        return dict(manager_id=user_manager.manager_id)
    else:
        return dict(manager_id=None)


def is_manager(user_id, manager_id):
    return db((db.user_manager.user_id == user_id) & (db.user_manager.manager_id == manager_id)).count() > 0

def get_managed_users(user_id):
    managed_users = db(db.user_manager.manager_id == user_id).select(db.user_manager.user_id)
    return [row.user_id for row in managed_users]

def get_all_managed_users():
    managed_users = db((db.user_manager.user_id)).select(db.user_manager.user_id)
    return [row.user_id for row in managed_users]

def can_edit_task(user_id, task):
    return task.created_by == user_id or task.created_by in get_managed_users(user_id)

@action("users", method=["GET"])
@action.uses(db, auth.user)
def get_auth_data():
    rows= db(db.auth_user).select(db.auth_user.id, db.auth_user.first_name, db.auth_user.last_name)
    users = [row.as_dict() for row in rows]
    dict(users=users)
    print(users)
    return users

def has_cycle(user_id, potential_manager_id):
    current_id = potential_manager_id
    
    while True:
        if current_id == user_id:
            return True
        row = db(db.user_manager.user_id == current_id).select(db.user_manager.manager_id).first()
        if row:
            current_id = row.manager_id
        else:
            break
    
    return False

def assign_manager(user_id, manager_id):
    if has_cycle(user_id, manager_id):
        raise ValueError("Cannot assign manager due to cycle in hierarchy")
    
    existing_relation = db(db.user_manager.user_id == user_id).select().first()
    if existing_relation:
        existing_relation.update_record(manager_id=manager_id)
    else:
        db.user_manager.insert(user_id=user_id, manager_id=manager_id)
    
    db.commit()


def get_full_hierarchy(user_id):
    def get_subordinates(manager_id):
        subordinates = []
        rows = db(db.user_manager.manager_id == manager_id).select()
        for row in rows:
            user = db(db.auth_user.id == row.user_id).select(db.auth_user.id, db.auth_user.first_name, db.auth_user.last_name).first()
            if user:
                subordinates.append({
                    'id': user.id,
                    'first_name': user.first_name,
                    'last_name': user.last_name,
                    'subordinates': get_subordinates(user.id)
                })
        return subordinates

    manager = db(db.auth_user.id == user_id).select(db.auth_user.id, db.auth_user.first_name, db.auth_user.last_name).first()
    if not manager:
        return None

    hierarchy = {
        'id': manager.id,
        'first_name': manager.first_name,
        'last_name': manager.last_name,
        'subordinates': get_subordinates(manager.id)
    }
    return hierarchy

# Example usage
user_hierarchy = get_full_hierarchy(1)
print(user_hierarchy)
