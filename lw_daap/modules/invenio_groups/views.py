# -*- coding: utf-8 -*-
#
# This file is part of Lifewatch DAAP.
# Copyright (C) 2015 Ana Yaiza Rodriguez Marrero.
#
# Lifewatch DAAP is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# Lifewatch DAAP is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with Lifewatch DAAP. If not, see <http://www.gnu.org/licenses/>.

#
# This file is part of Invenio.
# Copyright (C) 2012, 2013, 2014, 2015 CERN.
#
# Invenio is free software; you can redistribute it and/or
# modify it under the terms of the GNU General Public License as
# published by the Free Software Foundation; either version 2 of the
# License, or (at your option) any later version.
#
# Invenio is distributed in the hope that it will be useful, but
# WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
# General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with Invenio; if not, write to the Free Software Foundation, Inc.,
# 59 Temple Place, Suite 330, Boston, MA 02111-1307, USA.

"""Groups Settings Blueprint."""

from __future__ import absolute_import, print_function, unicode_literals

from urlparse import urlparse

from flask import Blueprint, flash, redirect, \
    render_template, request, url_for

from flask_breadcrumbs import default_breadcrumb_root, register_breadcrumb

from flask_login import current_user

from flask_menu import register_menu

from invenio.base.decorators import wash_arguments
from invenio.base.i18n import _
from invenio.ext.principal import permission_required

from invenio.modules.accounts.models import User

from sqlalchemy.exc import IntegrityError

from lw_daap.ext.login import login_required

from .forms import GroupForm, NewMemberForm
from .models import Group, Membership

entries_per_page = 4
blueprint = Blueprint(
    'groups_settings', __name__,
    url_prefix="/groups",
    template_folder='templates',
    static_folder='static',
)


default_breadcrumb_root(blueprint, '.settings.groups')


def get_group_name(id_group):
    """Used for breadcrumb dynamic_list_constructor."""
    group = Group.query.get(id_group)
    if group is not None:
        return group.name


@blueprint.route('/index', methods=['GET'])
@blueprint.route('/', methods=['GET'])
@register_menu(
    blueprint, 'settings.groups',
    _('%(icon)s My Groups', icon='<i class="fa fa-users fa-fw"></i>'),
    order=2,
    active_when=lambda: request.endpoint.startswith("groups_settings.")
)
@register_breadcrumb(blueprint, '.', _('Groups'))
@login_required
@permission_required('usegroups')
@wash_arguments({
    'mpage': (int, 1),
    'qpage': (int, 1),
    'per_page': (int, entries_per_page),
    'q': (unicode, ''),
})
def index(mpage, qpage, per_page, q):
    """List all user memberships."""
    # if current_user.is_admin:
    #     groups = Group.query
    # else:

    # Member Groups
    m_groups = Group.query_by_user(current_user, eager=True)
    m_groups = m_groups.paginate(mpage, per_page=per_page)

    q_groups = None
    # Query Groups
    if q:
        q_groups = Group.search(Group.query, q)
        q_groups = q_groups.paginate(qpage, per_page=per_page)

    requests = Membership.query_requests(current_user).count()
    invitations = Membership.query_invitations(current_user).count()

    return render_template(
        'groups/index.html',
        m_groups=m_groups,
        q_groups=q_groups,
        requests=requests,
        invitations=invitations,
        mpage=mpage,
        qpage=qpage,
        per_page=per_page,
        q=q
    )


@blueprint.route('/requests', methods=['GET'])
@register_breadcrumb(blueprint, '.requests', _('Requests'))
@login_required
@permission_required('usegroups')
@wash_arguments({
    'page': (int, 1),
    'per_page': (int, entries_per_page),
})
def requests(page, per_page):
    """List all pending memberships, listed only for group admins."""
    memberships = Membership.query_requests(current_user, eager=True).all()

    return render_template(
        'groups/pending.html',
        memberships=memberships,
        requests=True,
        page=page,
        per_page=per_page,
    )


@blueprint.route('/invitations', methods=['GET'])
@register_breadcrumb(blueprint, '.Invitations', _('Invitations'))
@login_required
@permission_required('usegroups')
@wash_arguments({
    'page': (int, 1),
    'per_page': (int, entries_per_page),
})
def invitations(page, per_page):
    """List all user pending memberships."""
    memberships = Membership.query_invitations(current_user, eager=True).all()

    return render_template(
        'groups/pending.html',
        memberships=memberships,
        page=page,
        per_page=per_page,
    )


@blueprint.route('/new', methods=['GET', 'POST'])
@register_breadcrumb(blueprint, '.new', _('New'))
@login_required
@permission_required('usegroups')
def new():
    """Create new group."""
    form = GroupForm(request.form)

    if form.validate_on_submit():
        try:
            group = Group.create(admins=[current_user], **form.data)
            group.add_member(current_user)
            flash(_('Group "%(name)s" created', name=group.name), 'success')
            return redirect(url_for(".index"))
        except IntegrityError:
            flash(_('Group creation failure'), 'error')

    return render_template(
        "groups/new.html",
        form=form,
    )


@blueprint.route('/<int:group_id>/manage', methods=['GET', 'POST'])
@blueprint.route('/<int:group_id>/', methods=['GET', 'POST'])
@register_breadcrumb(
    blueprint, '.manage', _('Manage'),
    dynamic_list_constructor=lambda:
        [{'text': get_group_name(request.view_args['group_id'])},
         {'text': _('Manage')}]
)
@login_required
@permission_required('usegroups')
def manage(group_id):
    """Manage your group."""
    group = Group.query.get_or_404(group_id)
    form = GroupForm(request.form, obj=group)
    if form.validate_on_submit():
        if group.can_edit(current_user):
            try:
                group.update(**form.data)
                flash(_('Group "%(name)s" was updated', name=group.name),
                      'success')
            except Exception as e:
                flash(str(e), 'error')
                return render_template(
                    "groups/new.html",
                    form=form,
                    group=group,
                )
        else:
            flash(
                _(
                    'You cannot edit group %(group_name)s',
                    group_name=group.name
                ),
                'error'
            )

    return render_template(
        "groups/new.html",
        form=form,
        group=group,
    )


@blueprint.route('/<int:group_id>/delete', methods=['POST'])
@login_required
@permission_required('usegroups')
def delete(group_id):
    """Delete group."""
    group = Group.query.get_or_404(group_id)

    if group.can_edit(current_user):
        try:
            group.delete()
        except Exception as e:
            flash(str(e), "error")
            return redirect(url_for(".index"))

        flash(_('Successfully removed group "%(group_name)s"',
                group_name=group.name), 'success')
        return redirect(url_for(".index"))

    flash(
        _(
            'You cannot delete the group %(group_name)s',
            group_name=group.name
        ),
        'error'
    )
    return redirect(url_for(".index"))


@blueprint.route('/<int:group_id>/members', methods=['GET', 'POST'])
@login_required
@register_breadcrumb(
    blueprint, '.members', _('Members'),
    dynamic_list_constructor=lambda:
        [{'text': get_group_name(request.view_args['group_id'])},
         {'text': _('Members')}]
)
@permission_required('usegroups')
@wash_arguments({
    'page': (int, 1),
    'per_page': (int, entries_per_page),
    'q': (unicode, ''),
    's': (unicode, ''),
})
def members(group_id, page, per_page, q, s):
    """List user group members."""
    group = Group.query.get_or_404(group_id)
    if group.can_see_members(current_user):
        members = Membership.query_by_group(group_id, with_invitations=True)
        if q:
            members = Membership.search(members, q)
        if s:
            members = Membership.order(members, Membership.state, s)
        members = members.paginate(page, per_page=per_page)

        return render_template(
            "groups/members.html",
            group=group,
            members=members,
            page=page,
            per_page=per_page,
            q=q,
            s=s,
        )

    flash(
        _(
            'You are not allowed to see members of this group %(group_name)s.',
            group_name=group.name
        ),
        'error'
    )
    return redirect(url_for('.index'))


@blueprint.route('/<int:group_id>/leave', methods=['POST'])
@login_required
@permission_required('usegroups')
def leave(group_id):
    """Leave group."""
    group = Group.query.get_or_404(group_id)

    if group.can_leave(current_user):
        try:
            group.remove_member(current_user)
        except Exception as e:
            flash(str(e), "error")
            return redirect(url_for('.index'))

        flash(
            _(
                'You have successfully left %(group_name)s group.',
                group_name=group.name
            ),
            'success'
        )
        return redirect(url_for('.index'))

    flash(
        _(
            'You cannot leave the group %(group_name)s',
            group_name=group.name
        ),
        'error'
    )
    return redirect(url_for('.index'))


@blueprint.route('/<int:group_id>/members/<int:user_id>/approve',
                 methods=['POST'])
@login_required
@permission_required('usegroups')
def approve(group_id, user_id):
    """Approve a user."""
    membership = Membership.query.get_or_404((user_id, group_id))
    group = membership.group

    if group.can_edit(current_user):
        try:
            membership.accept()
        except Exception as e:
            flash(str(e), 'error')
            return redirect(url_for('.requests', group_id=membership.group.id))

        flash(_('%(user)s accepted to %(name)s group.',
                user=membership.user.email,
                name=membership.group.name), 'success')
        return redirect(url_for('.requests', group_id=membership.group.id))

    flash(
        _(
            'You cannot approve memberships for the group %(group_name)s',
            group_name=group.name
        ),
        'error'
    )
    return redirect(url_for('.index'))


@blueprint.route('/<int:group_id>/members/<int:user_id>/remove',
                 methods=['POST'])
@login_required
@permission_required('usegroups')
def remove(group_id, user_id):
    """Remove user from a group."""
    group = Group.query.get_or_404(group_id)
    user = User.query.get_or_404(user_id)

    if group.can_edit(current_user):
        try:
            group.remove_member(user)
        except Exception as e:
            flash(str(e), "error")
            return redirect(urlparse(request.referrer).path)

        flash(_('User %(user_email)s was removed from %(group_name)s group.',
                user_email=user.email, group_name=group.name), 'success')
        return redirect(urlparse(request.referrer).path)

    flash(
        _(
            'You cannot delete users the group %(group_name)s',
            group_name=group.name
        ),
        'error'
    )
    return redirect(url_for('.index'))


@blueprint.route('/<int:group_id>/members/accept',
                 methods=['POST'])
@login_required
@permission_required('usegroups')
def accept(group_id):
    """Accpet pending invitation."""
    membership = Membership.query.get_or_404((current_user.get_id(), group_id))

    # no permission check, because they are checked during Memberships creating

    try:
        membership.accept()
    except Exception as e:
        flash(str(e), 'error')
        return redirect(url_for('.invitations', group_id=membership.group.id))

    flash(_('You are now part of %(name)s group.',
            user=membership.user.email,
            name=membership.group.name), 'success')
    return redirect(url_for('.invitations', group_id=membership.group.id))


@blueprint.route('/<int:group_id>/members/reject',
                 methods=['POST'])
@login_required
@permission_required('usegroups')
def reject(group_id):
    """Reject invitation."""
    membership = Membership.query.get_or_404((current_user.get_id(), group_id))
    user = membership.user
    group = membership.group

    # no permission check, because they are checked during Memberships creating

    try:
        membership.reject()
    except Exception as e:
        flash(str(e), 'error')
        return redirect(url_for('.invitations', group_id=membership.group.id))

    flash(_('You have rejected invitation to %(name)s group.',
            user=user.email,
            name=group.name), 'success')
    return redirect(url_for('.invitations', group_id=membership.group.id))


@blueprint.route('/<int:group_id>/members/new', methods=['GET', 'POST'])
@login_required
@register_breadcrumb(blueprint, '.members.new', _('New'))
@permission_required('usegroups')
def new_member(group_id):
    """Add (invite) new member."""
    group = Group.query.get_or_404(group_id)

    if group.can_invite_others(current_user):
        form = NewMemberForm()

        if form.validate_on_submit():
            emails = filter(None, form.data['emails'].splitlines())
            group.invite_by_emails(emails)
            flash(_('Requests sent!'), 'success')
            return redirect(url_for('.members', group_id=group.id))

        return render_template(
            "groups/new_member.html",
            group=group,
            form=form
        )

    flash(
        _(
            'You cannot invite user or yourself (i.e. join) to the group '
            '%(group_name)s',
            group_name=group.name
        ),
        'error'
    )
    return redirect(url_for('.index'))


@blueprint.route('/<int:group_id>/join', methods=['GET', 'POST'])
@login_required
# @register_breadcrumb(blueprint, '.members.new', _('New'))
@permission_required('usegroups')
def join(group_id):
    """Add (invite) new member."""
    group = Group.query.get_or_404(group_id)

    if group.can_join(current_user):
        group.subscribe(current_user)
    # flash(
    #     _(
    #         'You cannot invite yourself to the group '
    #         '%(group_name)s',
    #         group_name=group.name
    #       ),
    #       'error'
    # )
    return redirect(url_for('.index'))
