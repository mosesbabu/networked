from flask import (
    Blueprint,
    abort,
    flash,
    redirect,
    render_template,
    request,
    url_for,
    jsonify)
from flask_login import current_user, login_required
from flask_rq import get_queue

from app import db
from app.blueprints.admin.forms import (
    ChangeAccountTypeForm,
    ConfirmAccountForm,
    ChangeUserEmailForm,
    ChangeUserNameForm,
    InviteUserForm,
    NewUserForm,
    ChangeProfileForm
)
from app.decorators import admin_required
from app.email import send_email
from app.models import EditableHTML, Role, User, Post, Question, Organisation, Job, Message, ContactMessage, Service, Product, Event, Promo

admin = Blueprint('admin', __name__)


@admin.route('/')
@login_required
@admin_required
def index():
    """Admin dashboard page."""
    return render_template('admin/index.html')


@admin.route('/users/unconfirmed')
@login_required
@admin_required
def unconfirmed_users():
    """View all unconfirmed users."""
    users = db.session.query(User).filter(User.confirmed=='false').all()
    return render_template(
        'admin/unconfirmed_users.html', users=users)


@admin.route('/new-user', methods=['GET', 'POST'])
@login_required
@admin_required
def new_user():
    """Create a new user."""
    form = NewUserForm()
    password = form.password.data
    if form.validate_on_submit():
        user = User(
            role=form.role.data,
            first_name=form.first_name.data,
            last_name=form.last_name.data,
            email=form.email.data,
            password=form.password.data)
        db.session.add(user)
        db.session.commit()
        invite_link = url_for('account.login', _external=True)
        invite_by = User.query.filter(User.id == current_user.id).first()
        get_queue().enqueue(
            send_email,
            recipient=user.email,
            subject='You Are Invited To Join',
            template='account/email/created_account',
            user=user,
            invite_link=invite_link,
            invite_by=invite_by,
            password=password
        )
        flash('User {} successfully created'.format(user.full_name),
              'form-success')
    return render_template('admin/new_user.html', form=form)


@admin.route('/invite-user', methods=['GET', 'POST'])
@login_required
@admin_required
def invite_user():
    """Invites a new user to create an account and set their own password."""
    form = InviteUserForm()
    if form.validate_on_submit():
        user = User(
            role=form.role.data,
            first_name=form.first_name.data,
            last_name=form.last_name.data,
            email=form.email.data)
        db.session.add(user)
        db.session.commit()
        token = user.generate_confirmation_token()
        invite_link = url_for(
            'account.join_from_invite',
            user_id=user.id,
            token=token,
            _external=True)
        invite_by = User.query.filter(User.id == current_user.id).first()
        get_queue().enqueue(
            send_email,
            recipient=user.email,
            subject='You Are Invited To Join',
            template='account/email/invite',
            user=user,
            invite_link=invite_link,
            invite_by=invite_by
        )
        flash('User {} successfully invited'.format(user.full_name),
              'form-success')
    return render_template('admin/new_user.html', form=form)


@admin.route('/users')
@login_required
@admin_required
def registered_users():
    """View all registered users."""
    users = User.query.all()
    roles = Role.query.all()
    return render_template(
        'admin/registered_users.html', users=users, roles=roles)


@admin.route('/user/<int:user_id>')
@admin.route('/user/<int:user_id>/info')
@login_required
@admin_required
def user_info(user_id):
    """View a user's profile."""
    user = User.query.filter_by(id=user_id).first()
    if user is None:
        abort(404)
    return render_template('admin/manage_user.html', user=user)


@admin.route('/user/<int:user_id>/change-email', methods=['GET', 'POST'])
@login_required
@admin_required
def change_user_email(user_id):
    """Change a user's email."""
    user = User.query.filter_by(id=user_id).first()
    if user is None:
        abort(404)
    form = ChangeUserEmailForm()
    if form.validate_on_submit():
        user.email = form.email.data
        db.session.add(user)
        db.session.commit()
        flash('Email for user {} successfully changed to {}.'.format(
            user.full_name, user.email), 'form-success')
    return render_template('admin/manage_user.html', user=user, form=form)



@admin.route('/user/<int:user_id>/change-name', methods=['GET', 'POST'])
@login_required
@admin_required
def change_user_name(user_id):
    """Change a user's first and last names."""
    user = User.query.filter_by(id=user_id).first()
    if user is None:
        abort(404)
    form = ChangeUserNameForm()
    if form.validate_on_submit():
        user.first_name = form.first_name.data
        user.last_name = form.last_name.data
        db.session.add(user)
        db.session.commit()
        flash('First and last names changes successfully', 'form-success')
    return render_template('admin/manage_user.html', user=user, form=form)

@admin.route('/user/<int:user_id>/edit-profile', methods=['GET', 'POST'])
@login_required
@admin_required
def change_profile_details(user_id):
    """Respond to existing user's request to change their profile details."""
    user = User.query.filter_by(id=user_id).first()
    if user is None:
        abort(404)
    form = ChangeProfileForm(obj=user)
    if request.method == 'POST':
        if form.validate_on_submit():
            if form.validate_on_submit():
                form.populate_obj(user)
                db.session.add(user)
                if request.files['photo']:
                    image_filename = images.save(request.files['photo'])
                    image_url = images.url(image_filename)
                    picture_photo = Photo.query.filter_by(user_id=current_user.id).first()
                    if not picture_photo:
                        picture_photo = Photo(
                            image_filename=image_filename,
                            image_url=image_url,
                            user_id=current_user.id,
                        )
                    else:
                        picture_photo.image_filename = image_filename
                        picture_photo.image_url = image_url
                    db.session.add(picture_photo)
                db.session.commit()
                flash('You have successfully updated the profile',
                      'success')
                return redirect(url_for('admin.registered_users'))
            else:
                flash('Unsuccessful.', 'warning')
    return render_template('account/edit_profile.html', form=form)

@admin.route(
    '/user/<int:user_id>/change-account-type', methods=['GET', 'POST'])
@login_required
@admin_required
def change_account_type(user_id):
    """Change a user's account type."""
    if current_user.id == user_id:
        flash('You cannot change the type of your own account. Please ask '
              'another administrator to do this.', 'error')
        return redirect(url_for('admin.user_info', user_id=user_id))

    user = User.query.get(user_id)
    if user is None:
        abort(404)
    form = ChangeAccountTypeForm()
    if form.validate_on_submit():
        user.role = form.role.data
        db.session.add(user)
        db.session.commit()
        flash('Role for user {} successfully changed to {}.'.format(
            user.full_name, user.role.name), 'form-success')
    return render_template('admin/manage_user.html', user=user, form=form)


@admin.route(
    '/user/<int:user_id>/change-account-confirmation', methods=['GET', 'POST'])
@login_required
@admin_required
def change_account_confirmation(user_id):
    """Change a user's account type."""
    if current_user.id == user_id:
        flash('You cannot change the type of your own account. Please ask '
              'another administrator to do this.', 'error')
        return redirect(url_for('admin.user_info', user_id=user_id))

    user = User.query.get(user_id)
    if user is None:
        abort(404)
    form = ConfirmAccountForm()
    if form.validate_on_submit():
        user.confirmed = form.confirmed.data
        db.session.add(user)
        db.session.commit()
        flash('User confirmed', 'form-success')
    return render_template('admin/manage_user.html', user=user, form=form)


@admin.route('/user/<int:user_id>/delete')
@login_required
@admin_required
def delete_user_request(user_id):
    user = User.query.filter_by(id=user_id).first()
    if user is None:
        abort(404)
    return render_template('admin/manage_user.html', user=user)


@admin.route('/user/<int:user_id>/_delete')
@login_required
@admin_required
def delete_user(user_id):
    """Delete a user's account."""
    if current_user.id == user_id:
        flash('You cannot delete your own account. Please ask another '
              'administrator to do this.', 'error')
    else:
        user = User.query.filter_by(id=user_id).first()
        db.session.delete(user)
        db.session.commit()
        flash('Successfully deleted user %s.' % user.full_name, 'success')
    return redirect(url_for('admin.registered_users'))


@admin.route('/text/<text_type>', methods=['GET'])
@login_required
@admin_required
def text(text_type):
    editable_html_obj = EditableHTML.get_editable_html(text_type)
    return jsonify({
        'status': 1,
        'editable_html_obj': editable_html_obj.serialize
    })


@admin.route('/texts', methods=['POST', 'GET'])
@login_required
@admin_required
def texts():
    editable_html_obj = EditableHTML.get_editable_html('contact')
    if request.method == 'POST':
        edit_data = request.form.get('edit_data')
        editor_name = request.form.get('editor_name')

        editor_contents = EditableHTML.query.filter_by(
            editor_name=editor_name).first()
        if editor_contents is None:
            editor_contents = EditableHTML(editor_name=editor_name)
        editor_contents.value = edit_data

        db.session.add(editor_contents)
        db.session.commit()
        flash('Successfully updated text.', 'success')
        return redirect(url_for('admin.texts'))
    return render_template('admin/texts/index.html', editable_html_obj=editable_html_obj)


@admin.route('/services', defaults={'page': 1}, methods=['GET'])
@admin.route('/services/<int:page>', methods=['GET'])
@login_required
@admin_required
def services(page):
    services_result = Service.query.paginate(page, per_page=100)
    return render_template('admin/services/browse.html', services=services_result)

@admin.route('/promos', defaults={'page': 1}, methods=['GET'])
@admin.route('/promos/<int:page>', methods=['GET'])
@login_required
@admin_required
def promos(page):
    promos_result = Promo.query.paginate(page, per_page=100)
    return render_template('admin/promos/browse.html', promos=promos_result)

@admin.route('/products', defaults={'page': 1}, methods=['GET'])
@admin.route('/products/<int:page>', methods=['GET'])
@login_required
@admin_required
def products(page):
    products_result = Product.query.paginate(page, per_page=100)
    return render_template('admin/products/browse.html', products=products_result)

@admin.route('/events', defaults={'page': 1}, methods=['GET'])
@admin.route('/events/<int:page>', methods=['GET'])
@login_required
@admin_required
def events(page):
    events_result = Event.query.paginate(page, per_page=100)
    return render_template('admin/events/browse.html', events=events_result)

@admin.route('/posts', defaults={'page': 1}, methods=['GET'])
@admin.route('/posts/<int:page>', methods=['GET'])
@login_required
@admin_required
def posts(page):
    posts_result = Post.query.paginate(page, per_page=100)
    return render_template('admin/posts/browse.html', posts=posts_result)


@admin.route('/post/<int:post_id>/_delete', methods=['POST'])
@login_required
@admin_required
def delete_post(post_id):
    post = Post.query.filter_by(id=post_id).first()
    db.session.delete(post)
    db.session.commit()
    flash('Successfully deleted post.', 'success')
    return redirect(url_for('admin.posts'))


@admin.route('/questions', defaults={'page': 1}, methods=['GET'])
@admin.route('/questions/<int:page>', methods=['GET'])
@login_required
@admin_required
def questions(page):
    questions_result = Question.query.paginate(page, per_page=100)
    return render_template('admin/questions/browse.html', questions=questions_result)


@admin.route('/question/<int:question_id>/_delete', methods=['POST'])
@login_required
@admin_required
def delete_question(question_id):
    question = Question.query.filter_by(id=question_id).first()
    db.session.delete(question)
    db.session.commit()
    flash('Successfully deleted a question.', 'success')
    return redirect(url_for('admin.questions'))

@admin.route('/service/<int:service_id>/_delete', methods=['POST'])
@login_required
@admin_required
def delete_service(service_id):
    service = Service.query.filter_by(id=service_id).first()
    db.session.delete(service)
    db.session.commit()
    flash('Successfully deleted a service.', 'success')
    return redirect(url_for('admin.services'))

@admin.route('/event/<int:event_id>/_delete', methods=['POST'])
@login_required
@admin_required
def delete_event(event_id):
    event = Event.query.filter_by(id=event_id).first()
    db.session.delete(event)
    db.session.commit()
    flash('Successfully deleted an event.', 'success')
    return redirect(url_for('admin.events'))

@admin.route('/product/<int:product_id>/_delete', methods=['POST'])
@login_required
@admin_required
def delete_product(product_id):
    product = Product.query.filter_by(id=product_id).first()
    db.session.delete(product)
    db.session.commit()
    flash('Successfully deleted a product.', 'success')
    return redirect(url_for('admin.products'))

@admin.route('/promo/<int:promo_id>/_delete', methods=['POST'])
@login_required
@admin_required
def delete_promo(promo_id):
    promo = Promo.query.filter_by(id=promo_id).first()
    db.session.delete(promo)
    db.session.commit()
    flash('Successfully deleted a promo.', 'success')
    return redirect(url_for('admin.promos'))


@admin.route('/orgs', defaults={'page': 1}, methods=['GET'])
@admin.route('/orgs/<int:page>', methods=['GET'])
@login_required
@admin_required
def orgs(page):
    orgs = Organisation.query.paginate(page, per_page=100)
    return render_template('admin/orgs/browse.html', orgs=orgs)


@admin.route('/org/<int:org_id>/_delete', methods=['POST'])
@login_required
@admin_required
def delete_org(org_id):
    org = Organisation.query.filter_by(id=org_id).first()
    db.session.delete(org)
    db.session.commit()
    flash('Successfully deleted Organisation.', 'success')
    return redirect(url_for('admin.orgs'))


@admin.route('/jobs', defaults={'page': 1}, methods=['GET'])
@admin.route('/jobs/<int:page>', methods=['GET'])
@login_required
@admin_required
def jobs(page):
    jobs_result = Job.query.paginate(page, per_page=100)
    return render_template('admin/jobs/browse.html', jobs=jobs_result)


@admin.route('/job/<int:job_id>/_delete', methods=['POST'])
@login_required
@admin_required
def delete_job(job_id):
    job = Job.query.filter_by(id=job_id).first()
    db.session.delete(job)
    db.session.commit()
    flash('Successfully deleted Job.', 'success')
    return redirect(url_for('admin.jobs'))


@admin.route('/messages', defaults={'page': 1}, methods=['GET'])
@admin.route('/messages/<int:page>', methods=['GET'])
@login_required
@admin_required
def messages(page):
    messages_result = Message.query.paginate(page, per_page=100)
    return render_template('admin/messages/browse.html', messages=messages_result)


@admin.route('/message/<int:message_id>/_delete', methods=['POST'])
@login_required
@admin_required
def delete_message(message_id):
    message = Message.query.filter_by(id=message_id).first()
    db.session.delete(message)
    db.session.commit()
    flash('Successfully deleted Message.', 'success')
    return redirect(url_for('admin.messages'))


@admin.route('/contact_messages', defaults={'page': 1}, methods=['GET'])
@admin.route('/contact_messages/<page>', methods=['GET'])
@login_required
@admin_required
def contact_messages(page):
    contact_messages_result = ContactMessage.query.paginate(page, per_page=100)
    return render_template('admin/contact_messages/browse.html', contact_messages=contact_messages_result)


@admin.route('/contact_message/<message_id>', methods=['GET'])
@login_required
@admin_required
def view_contact_message(message_id):
    message = ContactMessage.query.filter_by(id=message_id).first_or_404()
    return render_template('admin/contact_messages/view.html', contact_message=message)


@admin.route('/contact_messages/<int:message_id>/_delete', methods=['POST'])
@login_required
@admin_required
def delete_contact_message(message_id):
    message = ContactMessage.query.filter_by(id=message_id).first()
    db.session.delete(message)
    db.session.commit()
    flash('Successfully deleted Message.', 'success')
    return redirect(url_for('admin.contact_messages'))
