# Copyright © 2019-2020 Red Hat, Inc.
#
# This file is part of Bodhi.
#
# This program is free software; you can redistribute it and/or
# modify it under the terms of the GNU General Public License
# as published by the Free Software Foundation; either version 2
# of the License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA  02110-1301, USA.
"""Handle tagging builds for an update in Koji."""

import logging
import typing

import koji  # noqa: 401

from bodhi.server import buildsys, util
from bodhi.server.models import Update


log = logging.getLogger(__name__)


def main(alias: str, builds: typing.List[str]):
    """Handle tagging builds for an update in Koji.

    Args:
        alias: an Update alias
        builds: list of new build added to the update.
    """
    koji = buildsys.get_session()
    koji.multicall = True
    db_factory = util.transactional_session_maker()
    try:
        with db_factory() as session:
            update = session.query(Update).filter_by(alias=alias).first()
        if update is not None:
            tag_builds(update, builds, koji)
    except Exception:
        log.exception("There was an error handling tagging builds in koji")
    finally:
        db_factory._end_session()


def tag_builds(update: Update, builds: typing.List[str],
               koji: typing.Union[koji.ClientSession, buildsys.DevBuildsys]):
    """Tag the update builds in koji.

    Args:
        update: an Update object
        builds: list of new build added to the update.
        koji: Koji client.
    """
    for build in builds:
        if update.from_tag:
            # this is a sidetag based update. use the sidetag pending signing tag
            side_tag_pending_signing = update.release.get_pending_signing_side_tag(
                update.from_tag)
            koji.tagBuild(side_tag_pending_signing, build)
        elif update.release.pending_signing_tag:
            # Add the release's pending_signing_tag to all new builds
            koji.tagBuild(update.release.pending_signing_tag, build)
        else:
            # EL6 doesn't have these, and that's okay...
            # We still warn in case the config gets messed up.
            log.warning(f'{update.release.name} has no pending_signing_tag')
    koji.multiCall()
