import logging
import time
import requests
import pyodbc
import pandas as pd
import tableauserverclient as tsc
import xml.etree.ElementTree as ET
import os

from contextlib import contextmanager
from tableauserverclient.server.endpoint.exceptions import NotSignedInError


class TableauService:
    def __init__(self, server_url, site_content_url, token_name, token_value, api_version=None, verify_ssl=True):
        self.server_url = server_url.rstrip('/')
        self.site_content_url = site_content_url
        self.token_name = token_name
        self.token_value = token_value
        self.api_version = api_version

        self.auth = tsc.PersonalAccessTokenAuth(
            token_name=self.token_name,
            personal_access_token=self.token_value,
            site_id=self.site_content_url
        )

        if api_version:
            self.server = tsc.Server(self.server_url, use_server_version=False)
            self.server.version = api_version
        else:
            self.server = tsc.Server(self.server_url, use_server_version=True)

        if not verify_ssl:
            self.server.add_http_options({'verify': False})

    from tableauserverclient.server.endpoint.exceptions import NotSignedInError

    @contextmanager
    def signin(self):
        auth_ctx = self.server.auth.sign_in(self.auth)
        try:
            auth_ctx.__enter__()
            yield self.server
        finally:
            try:
                auth_ctx.__exit__(None, None, None)
            except NotSignedInError:
                logging.warning("TSC session was already signed out or expired before sign_out completed.")

    def test_auth(self):
        try:
            with self.signin():
                return True
        except Exception:
            logging.exception("Authentication test failed")
            return False

    def get_projects(self):
        with self.signin() as server:
            return sorted(list(tsc.Pager(server.projects)), key=lambda p: (p.name or "").lower())

    def get_groups(self):
        with self.signin() as server:
            return sorted(list(tsc.Pager(server.groups)), key=lambda g: (g.name or "").lower())

    def get_users(self):
        with self.signin() as server:
            req = tsc.RequestOptions()
            req.pagesize = 1000
            return sorted(list(tsc.Pager(server.users, req)), key=lambda u: (u.name or "").lower())

    def get_users_display_map(self):
        with self.signin() as server:
            req = tsc.RequestOptions()
            req.pagesize = 1000
            display_map = {}
            users = sorted(list(tsc.Pager(server.users, req)), key=lambda u: (u.name or "").lower())
            for user in users:
                display = f"{user.name} - {user.fullname}"
                display_map[display] = user
            return display_map
            
    def _get_paged_items(self, endpoint, page_size=1000):
        req = tsc.RequestOptions()
        req.pagesize = page_size
        return list(tsc.Pager(endpoint, req))

    def get_workbooks_grouped_by_project(self):
        with self.signin() as server:
            projects = list(tsc.Pager(server.projects))
            project_by_id = {p.id: p.name for p in projects}
            grouped = {}

            for workbook in self._get_paged_items(server.workbooks, 1000):
                project_name = project_by_id.get(workbook.project_id, "Unknown Project")
                grouped.setdefault(project_name, []).append(workbook)

            for project_name in grouped:
                grouped[project_name] = sorted(grouped[project_name], key=lambda w: (w.name or "").lower())

            return grouped

    def refresh_workbooks(self, project_names=None, workbook_names=None):
        project_names = set(project_names or [])
        workbook_names = set(workbook_names or [])
        refreshed = []

        with self.signin() as server:
            projects = list(tsc.Pager(server.projects))
            project_ids = {p.id for p in projects if not project_names or p.name in project_names}

            for workbook in self._get_paged_items(server.workbooks, 1000):
                if workbook.project_id not in project_ids:
                    continue
                if workbook_names and workbook.name not in workbook_names:
                    continue

                logging.info(f"Refreshing workbook: {workbook.name} ({workbook.id})")
                server.workbooks.refresh(workbook)
                refreshed.append(workbook.name)

        return refreshed

    def update_connection_server_names(self, project_names, old_server, new_server):
        results = {
            'workbooks_updated': [],
            'datasources_updated': [],
        }

        with self.signin() as server:
            projects = list(tsc.Pager(server.projects))
            project_ids = {p.id for p in projects if p.name in project_names}

            for workbook in self._get_paged_items(server.workbooks, 1000):
                if workbook.project_id not in project_ids:
                    continue

                server.workbooks.populate_connections(workbook)
                changed = False

                for connection in getattr(workbook, 'connections', []):
                    server_address = (getattr(connection, 'server_address', None) or "").strip()
                    if old_server == '*' or old_server.lower() in server_address.lower():
                        logging.info(
                            f"Updating workbook connection server: workbook={workbook.name}, "
                            f"connection={connection.id}, old={server_address}, new={new_server}"
                        )
                        connection.server_address = new_server
                        server.workbooks.update_connection(workbook, connection)
                        changed = True

                if changed:
                    results['workbooks_updated'].append(workbook.name)

            for datasource in tsc.Pager(server.datasources):
                if datasource.project_id not in project_ids:
                    continue

                server.datasources.populate_connections(datasource)
                changed = False

                for connection in getattr(datasource, 'connections', []):
                    server_address = (getattr(connection, 'server_address', None) or "").strip()
                    if old_server == '*' or old_server.lower() in server_address.lower():
                        logging.info(
                            f"Updating datasource connection server: datasource={datasource.name}, "
                            f"connection={connection.id}, old={server_address}, new={new_server}"
                        )
                        connection.server_address = new_server
                        server.datasources.update_connection(datasource, connection)
                        changed = True

                if changed:
                    results['datasources_updated'].append(datasource.name)

        return results

    def update_connection_credentials(self, project_names, server_match, current_username, new_username=None, password=None):
        results = {
            'workbooks_updated': [],
            'datasources_updated': [],
        }

        with self.signin() as server:
            projects = list(tsc.Pager(server.projects))
            project_ids = {p.id for p in projects if p.name in project_names}

            for workbook in self._get_paged_items(server.workbooks, 1000):
                if workbook.project_id not in project_ids:
                    continue

                server.workbooks.populate_connections(workbook)
                changed = False

                for connection in getattr(workbook, 'connections', []):
                    conn_server = (getattr(connection, 'server_address', None) or "").strip()
                    conn_user = (getattr(connection, 'username', None) or "").strip()

                    server_matches = server_match == '*' or server_match.lower() in conn_server.lower()
                    user_matches = conn_user.lower() == current_username.lower()

                    if server_matches and user_matches:
                        logging.info(
                            f"Updating workbook connection credentials: workbook={workbook.name}, "
                            f"connection={connection.id}, user={conn_user}"
                        )
                        if new_username:
                            connection.username = new_username
                        if password:
                            connection.password = password
                        if hasattr(connection, 'embed_password') and password:
                            connection.embed_password = True

                        server.workbooks.update_connection(workbook, connection)
                        changed = True

                if changed:
                    results['workbooks_updated'].append(workbook.name)

            for datasource in tsc.Pager(server.datasources):
                if datasource.project_id not in project_ids:
                    continue

                server.datasources.populate_connections(datasource)
                changed = False

                for connection in getattr(datasource, 'connections', []):
                    conn_server = (getattr(connection, 'server_address', None) or "").strip()
                    conn_user = (getattr(connection, 'username', None) or "").strip()

                    server_matches = server_match == '*' or server_match.lower() in conn_server.lower()
                    user_matches = conn_user.lower() == current_username.lower()

                    if server_matches and user_matches:
                        logging.info(
                            f"Updating datasource connection credentials: datasource={datasource.name}, "
                            f"connection={connection.id}, user={conn_user}"
                        )
                        if new_username:
                            connection.username = new_username
                        if password:
                            connection.password = password
                        if hasattr(connection, 'embed_password') and password:
                            connection.embed_password = True

                        server.datasources.update_connection(datasource, connection)
                        changed = True

                if changed:
                    results['datasources_updated'].append(datasource.name)

        return results

    def add_user(self, username, site_role='Viewer', group_names=None):
        group_names = set(group_names or [])

        with self.signin() as server:
            new_user = tsc.UserItem(name=username, site_role=site_role)
            created_user = server.users.add(new_user)
            created_user = server.users.get_by_id(created_user.id)

            if created_user.site_role == 'Unlicensed':
                server.users.remove(created_user.id)
                raise RuntimeError("No licenses available to add the user.")

            if group_names:
                groups = list(tsc.Pager(server.groups))
                groups_by_name = {g.name: g for g in groups}

                for group_name in group_names:
                    group = groups_by_name.get(group_name)
                    if group:
                        server.groups.add_user(group, created_user.id)

            return created_user

    def remove_user(self, user_id):
        with self.signin() as server:
            server.users.remove(user_id)

    def generate_user_report(self):
        with self.signin() as server:
            req = tsc.RequestOptions()
            req.pagesize = 1000
            users = list(tsc.Pager(server.users, req))
            data_sources = list(tsc.Pager(server.datasources))
            workbooks = self._get_paged_items(server.workbooks, 1000)

            owners = {ds.owner_id for ds in data_sources}
            owners.update({wb.owner_id for wb in workbooks})

            user_info = pd.DataFrame([
                {
                    'User ID': user.id,
                    'User Name': user.name,
                    'User Display Name': user.fullname,
                    'User Email Address': user.email,
                    'User Domain': getattr(user, 'domain_name', ''),
                    'User Site Role': user.site_role,
                    'Content Owner': user.id in owners
                }
                for user in users
            ])

            return user_info.sort_values(by='Content Owner', ascending=False)

    def generate_group_report(self):
        with self.signin() as server:
            groups = list(tsc.Pager(server.groups))
            for group in groups:
                server.groups.populate_users(group)

            group_info = pd.DataFrame([
                {
                    'Group ID': group.id,
                    'Group Name': group.name,
                    'Group Domain': group.domain_name,
                    'Users': [user.id for user in group.users]
                }
                for group in groups
            ])

            if not group_info.empty:
                group_info = group_info.explode(column='Users')

            req = tsc.RequestOptions()
            req.pagesize = 1000
            users = list(tsc.Pager(server.users, req))
            user_info = pd.DataFrame([
                {
                    'User ID': user.id,
                    'User Name': user.name,
                    'User Display Name': user.fullname,
                    'User Email Address': user.email,
                    'User Domain': getattr(user, 'domain_name', ''),
                    'User Site Role': user.site_role
                }
                for user in users
            ])

            if group_info.empty:
                return pd.DataFrame(columns=[
                    'Group ID', 'Group Name', 'Group Domain',
                    'Users', 'User Name', 'User Display Name',
                    'User Email Address', 'User Domain', 'User Site Role'
                ])

            return group_info.merge(
                right=user_info,
                how='left',
                left_on='Users',
                right_on='User ID'
            ).drop(columns=['User ID'])

    def generate_project_report(self):
        with self.signin() as server:
            projects = list(tsc.Pager(server.projects))
            req = tsc.RequestOptions()
            req.pagesize = 1000
            users = list(tsc.Pager(server.users, req))

            project_info = pd.DataFrame([
                {
                    'Project ID': project.id,
                    'Project Name': project.name,
                    'Project Description': project.description,
                    'Project Owner ID': project.owner_id,
                    'Parent Project ID': project.parent_id
                }
                for project in projects
            ])

            user_info = pd.DataFrame([
                {
                    'User ID': user.id,
                    'User Display Name': user.fullname,
                    'User Email Address': user.email,
                    'User Site Role': user.site_role
                }
                for user in users
            ])

            if project_info.empty:
                return pd.DataFrame()

            return (
                project_info
                .merge(
                    right=project_info,
                    how='left',
                    left_on='Parent Project ID',
                    right_on='Project ID',
                    suffixes=('', ' Parent'),
                )
                .drop(columns=['Parent Project ID Parent', 'Project ID Parent'], errors='ignore')
                .rename(columns={
                    'Project Name Parent': 'Parent Project Name',
                    'Project Description Parent': 'Parent Project Description',
                    'Project Owner ID Parent': 'Parent Project Owner ID'
                })
                .merge(right=user_info, how='left', left_on='Project Owner ID', right_on='User ID')
                .drop(columns=['User ID'], errors='ignore')
                .rename(columns={
                    'User Display Name': 'Project Owner Name',
                    'User Email Address': 'Project Owner Email Address',
                    'User Site Role': 'Project Owner Site Role'
                })
                .merge(right=user_info, how='left', left_on='Parent Project Owner ID', right_on='User ID')
                .drop(columns=['User ID'], errors='ignore')
                .rename(columns={
                    'User Display Name': 'Parent Project Owner Name',
                    'User Email Address': 'Parent Project Owner Email Address',
                    'User Site Role': 'Parent Project Owner Site Role'
                })
            )

    def generate_workbook_report(self):
        with self.signin() as server:
            req = tsc.RequestOptions()
            req.pagesize = 1000
            workbooks = list(tsc.Pager(server.workbooks, req))
            users = list(tsc.Pager(server.users, req))

            rows = []
            for workbook in workbooks:
                wb = workbook

                created_at = getattr(wb, 'created_at', None) or getattr(wb, '_created_at', '')
                updated_at = getattr(wb, 'updated_at', None) or getattr(wb, '_updated_at', '')
                webpage_url = getattr(wb, 'webpage_url', None) or getattr(wb, '_webpage_url', '')
                project_id = getattr(wb, 'project_id', None) or getattr(wb, '_project_id', '')
                project_name = getattr(wb, 'project_name', None) or getattr(wb, '_project_name', '')
                size = getattr(wb, 'size', None) or getattr(wb, '_size', '')

                rows.append({
                    'Workbook ID': getattr(wb, 'id', None) or getattr(wb, '_id', ''),
                    'Workbook Owner ID': getattr(wb, 'owner_id', ''),
                    'Workbook Name': getattr(wb, 'name', ''),
                    'Workbook Created At': self._excel_safe_datetime(created_at),
                    'Workbook Updated At': self._excel_safe_datetime(updated_at),
                    'Workbook Content URL': webpage_url,
                    'Workbook Project ID': project_id,
                    'Workbook Project Name': project_name,
                    'Workbook Size (MB)': size,
                })

            workbook_info = pd.DataFrame(rows)

            user_info = pd.DataFrame([
                {
                    'User ID': user.id,
                    'User Display Name': user.fullname,
                    'User Email Address': user.email,
                    'User Site Role': user.site_role,
                }
                for user in users
            ])

            if workbook_info.empty:
                return pd.DataFrame()

            return (
                workbook_info
                .merge(
                    user_info,
                    how='left',
                    left_on='Workbook Owner ID',
                    right_on='User ID'
                )
                .drop(columns=['User ID'], errors='ignore')
                .rename(columns={
                    'User Display Name': 'Workbook Owner Name',
                    'User Email Address': 'Workbook Owner Email Address',
                    'User Site Role': 'Workbook Owner Site Role'
                })
            )

    def _excel_safe_datetime(self, value):
        if value is None or value == "":
            return ""
        try:
            if hasattr(value, "tzinfo") and value.tzinfo is not None:
                return value.replace(tzinfo=None)
        except Exception:
            pass
        return value
        
    def generate_datasource_report(self):
        with self.signin() as server:
            data_sources = list(tsc.Pager(server.datasources))
            req = tsc.RequestOptions()
            req.pagesize = 1000
            users = list(tsc.Pager(server.users, req))

            rows = []
            for data_source in data_sources:
                try:
                    full_ds = server.datasources.get_by_id(data_source.id)
                except Exception:
                    full_ds = data_source

                created_at = getattr(full_ds, 'created_at', None) or getattr(full_ds, '_created_at', '')
                updated_at = getattr(full_ds, 'updated_at', None) or getattr(full_ds, '_updated_at', '')

                rows.append({
                    'Data Source ID': getattr(full_ds, 'id', None) or getattr(full_ds, '_id', ''),
                    'Data Source Owner ID': getattr(full_ds, 'owner_id', ''),
                    'Data Source Name': getattr(full_ds, 'name', ''),
                    'Data Source Type': getattr(full_ds, 'datasource_type', None) or getattr(full_ds, '_datasource_type', ''),
                    'Data Source Created At': self._excel_safe_datetime(created_at),
                    'Data Source Updated At': self._excel_safe_datetime(updated_at),
                    'Data Source Project ID': getattr(full_ds, 'project_id', None) or getattr(full_ds, '_project_id', ''),
                    'Data Source Project Name': getattr(full_ds, 'project_name', None) or getattr(full_ds, '_project_name', ''),
                })

            data_source_info = pd.DataFrame(rows)

            user_info = pd.DataFrame([
                {
                    'User ID': user.id,
                    'User Display Name': user.fullname,
                    'User Email Address': user.email,
                    'User Site Role': user.site_role,
                }
                for user in users
            ])

            if data_source_info.empty:
                return pd.DataFrame()

            return (
                data_source_info
                .merge(
                    user_info,
                    how='left',
                    left_on='Data Source Owner ID',
                    right_on='User ID'
                )
                .drop(columns=['User ID'], errors='ignore')
                .rename(columns={
                    'User Display Name': 'Data Source Owner Name',
                    'User Email Address': 'Data Source Owner Email Address',
                    'User Site Role': 'Data Source Owner Site Role'
                })
            )

    def generate_favorites_report(self, ntlogin):
        with self.signin() as server:
            req = tsc.RequestOptions()
            req.pagesize = 1000
            users = list(tsc.Pager(server.users, req))

            target_user = next(
                (user for user in users if (user.name or "").strip().lower() == ntlogin.strip().lower()),
                None
            )

            if not target_user:
                raise RuntimeError(f"User not found: {ntlogin}")

            server.users.populate_favorites(target_user)
            all_favorites = []

            favorite_categories = [
                category for category in target_user.favorites.keys()
                if target_user.favorites[category]
            ]

            for category in favorite_categories:
                category_favorites = pd.DataFrame(
                    data=target_user.favorites[category],
                    columns=['Favorite']
                )
                category_favorites = category_favorites.assign(
                    favorite_id=category_favorites['Favorite'].apply(lambda favorite: favorite.id),
                    favorite_name=category_favorites['Favorite'].apply(lambda favorite: favorite.name),
                    favorite_category=category.title(),
                    favorite_project_id=category_favorites['Favorite'].apply(
                        lambda favorite: getattr(favorite, 'project_id', 'Not applicable')
                    ),
                    favorite_project_name=category_favorites['Favorite'].apply(
                        lambda favorite: getattr(favorite, 'project_name', 'Not applicable')
                    ),
                    user_id=target_user.id,
                    user_name=target_user.name,
                    user_display_name=target_user.fullname,
                    user_email_address=target_user.email,
                    user_site_role=target_user.site_role
                )
                all_favorites.append(category_favorites)

            if not all_favorites:
                return pd.DataFrame(columns=[
                    'Favorite ID', 'Favorite Name', 'Favorite Category',
                    'Favorite Project ID', 'Favorite Project Name',
                    'User ID', 'User Name', 'User Display Name',
                    'User Email Address', 'User Site Role'
                ])

            return (
                pd.concat(all_favorites, axis=0, ignore_index=True)
                .drop(columns=['Favorite'])
                .rename(lambda column: column.replace('_', ' ').title().replace('Id', 'ID'), axis=1)
            )

    def generate_subscriptions_report(self):
        with self.signin() as server:
            subscriptions = self._get_paged_items(server.subscriptions, 1000)
            req = tsc.RequestOptions()
            req.pagesize = 1000
            users = list(tsc.Pager(server.users, req))

            subscription_info = pd.DataFrame([
                {
                    'Subscription ID': subscription.id,
                    'Subscription Owner ID': subscription.user_id,
                    'Subscription Subject': subscription.subject,
                    'Subscription Content ID': subscription.target.id,
                    'Subscription Content Type': subscription.target.type,
                }
                for subscription in subscriptions
            ])

            user_info = pd.DataFrame([
                {
                    'User ID': user.id,
                    'User Display Name': user.fullname,
                    'User Email Address': user.email,
                    'User Site Role': user.site_role
                }
                for user in users
            ])

            if subscription_info.empty:
                return pd.DataFrame()

            return (
                subscription_info
                .merge(
                    right=user_info,
                    left_on='Subscription Owner ID',
                    right_on='User ID',
                    how='left'
                )
                .drop(columns=['User ID'], errors='ignore')
                .rename(columns={
                    'User Display Name': 'Subscription Owner Display Name',
                    'User Email Address': 'Subscription Owner Email Address',
                    'User Site Role': 'Subscription Owner Site Role'
                })
            )

    def generate_master_report(self):
        return {
            'Users': self.generate_user_report(),
        }
        
    def get_extensions_site_safe_list(self):
        signin_url = f"{self.server_url}/api/{self.server.version}/auth/signin"
        signin_payload = {
            "credentials": {
                "personalAccessTokenName": self.token_name,
                "personalAccessTokenSecret": self.token_value,
                "site": {
                    "contentUrl": self.site_content_url
                }
            }
        }

        headers = {
            "Content-Type": "application/json",
            "Accept": "application/json"
        }

        response = requests.post(signin_url, json=signin_payload, headers=headers)
        response.raise_for_status()

        data = response.json()
        token = data["credentials"]["token"]
        site_id = data["credentials"]["site"]["id"]

        try:
            url = f"{self.server_url}/api/{self.server.version}/sites/{site_id}/settings/extensions"
            headers = {
                "X-Tableau-Auth": token,
                "Accept": "application/json"
            }

            response = requests.get(url, headers=headers)
            response.raise_for_status()

            content_type = response.headers.get("Content-Type", "").lower()

            if "json" in content_type:
                payload = response.json()
                safe_list = payload.get("extensionsSiteSettings", {}).get("safeList", [])

                formatted = []
                for item in safe_list:
                    formatted.append(
                        f"URL: {item.get('url', '')}\n"
                        f"Full Data Allowed: {item.get('fullDataAllowed', '')}\n"
                        f"Prompt Needed: {item.get('promptNeeded', '')}"
                    )

                return formatted

            root = ET.fromstring(response.text)

            safe_list = []
            for elem in root.iter():
                tag = elem.tag.lower()
                if tag.endswith("safelist") and elem.text:
                    safe_list.append(elem.text.strip())

            return safe_list

        finally:
            try:
                signout_url = f"{self.server_url}/api/{self.server.version}/auth/signout"
                requests.post(signout_url, headers={"X-Tableau-Auth": token})
            except Exception:
                pass
            

    def _safe_int(self, value):
        try:
            return int(value or 0)
        except Exception:
            return 0

    def _format_mb(self, num):
        num = float(num or 0)
        for unit in ["MB", "GB", "TB"]:
            if num < 1024 or unit == "TB":
                return f"{num:,.2f} {unit}"
            num /= 1024
            
    def _format_storage_gb_from_mb(self, num):
        num = float(num or 0)
        return f"{num / 1024:,.2f} GB"

    def _format_storage_mb(self, num):
        num = float(num or 0)
        return f"{num:,.2f} MB"


    def generate_server_overview(self, progress_callback=None):
        def update(msg):
            if progress_callback:
                progress_callback(msg)

        with self.signin() as server:
            update("Snatching all the user info...")
            users = self._get_paged_items(server.users, 1000)

            update("Looking at your projects...")
            projects = self._get_paged_items(server.projects, 1000)

            update("Judging your workbooks...")
            workbooks = self._get_paged_items(server.workbooks, 1000)

            update("Poking around your data sources...")
            datasources = self._get_paged_items(server.datasources, 1000)

            update("Counting groups like a digital hall monitor...")
            groups = self._get_paged_items(server.groups, 1000)

            update("Reading subscriptions nobody remembers setting up...")
            subscriptions = self._get_paged_items(server.subscriptions, 1000)

            update("Doing suspiciously advanced math...")
            workbook_storage_mb = sum(
                float(getattr(wb, 'size', None) or getattr(wb, '_size', 0) or 0)
                for wb in workbooks
            )

            update("Calling Tableau REST API for datasource sizes...")
            datasource_storage_mb = self.get_datasource_storage_mb_rest()

            content_owner_ids = {
                getattr(wb, 'owner_id', None) for wb in workbooks if getattr(wb, 'owner_id', None)
            }
            content_owner_ids.update(
                {getattr(ds, 'owner_id', None) for ds in datasources if getattr(ds, 'owner_id', None)}
            )

            top_level_projects = [p for p in projects if not getattr(p, 'parent_id', None)]
            nested_projects = [p for p in projects if getattr(p, 'parent_id', None)]

            workbook_updates = [
                getattr(wb, 'updated_at', None) or getattr(wb, '_updated_at', None)
                for wb in workbooks
            ]
            workbook_updates = [d for d in workbook_updates if d is not None]
            latest_workbook_update = max(workbook_updates) if workbook_updates else None

            largest_workbook = None
            if workbooks:
                largest_workbook = max(
                    workbooks,
                    key=lambda wb: (getattr(wb, 'size', None) or getattr(wb, '_size', 0) or 0)
                )

            largest_workbook_size_mb = (
                (getattr(largest_workbook, 'size', None) or getattr(largest_workbook, '_size', 0) or 0)
                if largest_workbook else 0
            )
            logging.info("Starting job failure check for last 24 hours")
            update("Checking for failed Tableau jobs in the last 24 hours.")
            try:
                job_failures_24h = self.get_failed_jobs_last_24_hours(
                    hours=24,
                    progress_callback=progress_callback
                )
                job_failures_error = ""
            except Exception as exc:
                logging.exception("Failed to retrieve Tableau job failures")
                job_failures_24h = []
                job_failures_error = str(exc)
                
            logging.info("Completed job failure check: %s failures found", len(job_failures_24h))
            update("Putting everything into neat little boxes...")
            
            return {
                "server_url": self.server_url,
                "site_name": self.site_content_url or "Default",

                "users": len(users),
                "projects": len(projects),
                "top_level_projects": len(top_level_projects),
                "nested_projects": len(nested_projects),
                "workbooks": len(workbooks),
                "datasources": len(datasources),
                "groups": len(groups),
                "subscriptions": len(subscriptions),
                "content_owners": len(content_owner_ids),

                "workbook_storage_mb": workbook_storage_mb,
                "datasource_storage_mb": datasource_storage_mb,
                "total_storage_mb": workbook_storage_mb + datasource_storage_mb,
                "largest_workbook_size_mb": largest_workbook_size_mb,

                "workbook_storage_display": self._format_storage_gb_from_mb(workbook_storage_mb),
                "datasource_storage_display": self._format_storage_gb_from_mb(datasource_storage_mb),
                "total_storage_display": self._format_storage_gb_from_mb(workbook_storage_mb + datasource_storage_mb),

                "latest_workbook_update": latest_workbook_update,
                "largest_workbook_name": getattr(largest_workbook, "name", "N/A") if largest_workbook else "N/A",
                "largest_workbook_size_display": self._format_storage_mb(largest_workbook_size_mb),
                
                "job_failures_24h": job_failures_24h,
                "job_failures_24h_count": len(job_failures_24h),
                "job_failures_error": job_failures_error,
            }
            
    def get_datasource_storage_mb_rest(self):
        signin_url = f"{self.server_url}/api/{self.server.version}/auth/signin"
        signin_payload = {
            "credentials": {
                "personalAccessTokenName": self.token_name,
                "personalAccessTokenSecret": self.token_value,
                "site": {
                    "contentUrl": self.site_content_url
                }
            }
        }

        headers = {
            "Content-Type": "application/json",
            "Accept": "application/json"
        }

        response = requests.post(signin_url, json=signin_payload, headers=headers)
        response.raise_for_status()

        data = response.json()
        token = data["credentials"]["token"]
        site_id = data["credentials"]["site"]["id"]

        try:
            total_size_mb = 0
            page_number = 1
            page_size = 1000

            while True:
                url = (
                    f"{self.server_url}/api/{self.server.version}/sites/{site_id}/datasources"
                    f"?pageSize={page_size}&pageNumber={page_number}"
                )

                resp = requests.get(
                    url,
                    headers={
                        "X-Tableau-Auth": token,
                        "Accept": "application/json"
                    }
                )
                resp.raise_for_status()

                payload = resp.json()
                datasources = payload.get("datasources", {}).get("datasource", [])

                if not datasources:
                    break

                for ds in datasources:
                    total_size_mb += float(ds.get("size") or 0)

                pagination = payload.get("pagination", {})
                total_available = int(pagination.get("totalAvailable", 0))
                if page_number * page_size >= total_available:
                    break

                page_number += 1

            return total_size_mb

        finally:
            try:
                signout_url = f"{self.server_url}/api/{self.server.version}/auth/signout"
                requests.post(signout_url, headers={"X-Tableau-Auth": token})
            except Exception:
                pass
                
    def _rest_signin(self):
        signin_url = f"{self.server_url}/api/{self.server.version}/auth/signin"
        payload = {
            "credentials": {
                "personalAccessTokenName": self.token_name,
                "personalAccessTokenSecret": self.token_value,
                "site": {"contentUrl": self.site_content_url}
            }
        }
        headers = {"Content-Type": "application/json", "Accept": "application/json"}
        resp = requests.post(signin_url, json=payload, headers=headers)
        resp.raise_for_status()
        data = resp.json()["credentials"]
        return data["token"], data["site"]["id"]

    def _rest_signout(self, token):
        try:
            signout_url = f"{self.server_url}/api/{self.server.version}/auth/signout"
            requests.post(signout_url, headers={"X-Tableau-Auth": token})
        except Exception:
            pass
        
    def _get_project_permissions_rest(self, token, site_id, project_id, retries=3, delay=1.5):
        url = f"{self.server_url}/api/{self.server.version}/sites/{site_id}/projects/{project_id}/permissions"

        last_exc = None
        for attempt in range(1, retries + 1):
            try:
                resp = requests.get(
                    url,
                    headers={"X-Tableau-Auth": token, "Accept": "application/json"},
                    timeout=60
                )
                resp.raise_for_status()
                return resp.json()
            except requests.exceptions.RequestException as exc:
                last_exc = exc
                logging.warning(
                    f"Attempt {attempt}/{retries} failed for project permissions: project_id={project_id}, error={exc}"
                )
                if attempt < retries:
                    time.sleep(delay * attempt)

        raise last_exc

    def _get_workbook_permissions_rest(self, token, site_id, workbook_id, retries=3, delay=1.5):
        url = f"{self.server_url}/api/{self.server.version}/sites/{site_id}/workbooks/{workbook_id}/permissions"

        last_exc = None
        for attempt in range(1, retries + 1):
            try:
                resp = requests.get(
                    url,
                    headers={"X-Tableau-Auth": token, "Accept": "application/json"},
                    timeout=60
                )
                resp.raise_for_status()
                return resp.json()
            except requests.exceptions.RequestException as exc:
                last_exc = exc
                logging.warning(
                    f"Attempt {attempt}/{retries} failed for workbook permissions: workbook_id={workbook_id}, error={exc}"
                )
                if attempt < retries:
                    time.sleep(delay * attempt)

        raise last_exc

    def _get_datasource_permissions_rest(self, token, site_id, datasource_id, retries=3, delay=1.5):
        url = f"{self.server_url}/api/{self.server.version}/sites/{site_id}/datasources/{datasource_id}/permissions"

        last_exc = None
        for attempt in range(1, retries + 1):
            try:
                resp = requests.get(
                    url,
                    headers={"X-Tableau-Auth": token, "Accept": "application/json"},
                    timeout=60
                )
                resp.raise_for_status()
                return resp.json()
            except requests.exceptions.RequestException as exc:
                last_exc = exc
                logging.warning(
                    f"Attempt {attempt}/{retries} failed for datasource permissions: datasource_id={datasource_id}, error={exc}"
                )
                if attempt < retries:
                    time.sleep(delay * attempt)

        raise last_exc
        
            
    def _build_permission_inventory(self, project_names=None):
        with self.signin() as server:
            projects = list(tsc.Pager(server.projects))
            workbooks = list(tsc.Pager(server.workbooks))
            datasources = list(tsc.Pager(server.datasources))
            users = list(tsc.Pager(server.users))
            groups = list(tsc.Pager(server.groups))

        project_map = {p.id: p for p in projects}
        user_map = {u.id: u for u in users}
        group_map = {g.id: g for g in groups}

        selected_project_ids = None
        if project_names:
            selected_project_ids = {p.id for p in projects if p.name in project_names}

        if selected_project_ids is not None:
            workbooks = [w for w in workbooks if w.project_id in selected_project_ids]
            datasources = [d for d in datasources if d.project_id in selected_project_ids]
            projects = [p for p in projects if p.id in selected_project_ids]

        return {
            "projects": projects,
            "workbooks": workbooks,
            "datasources": datasources,
            "users": users,
            "groups": groups,
            "project_map": project_map,
            "user_map": user_map,
            "group_map": group_map,
        }
        
    def _normalize_grantee_capabilities(self, content_type, content_obj, payload, inventory):
        rows = []

        grantee_caps = payload.get("permissions", {}).get("granteeCapabilities", []) or []
        if isinstance(grantee_caps, dict):
            grantee_caps = [grantee_caps]

        project = inventory["project_map"].get(getattr(content_obj, "project_id", None))
        owner = inventory["user_map"].get(getattr(content_obj, "owner_id", None))

        for grantee in grantee_caps:
            user_id = None
            user_name = None
            group_id = None
            group_name = None
            target_type = None

            if "user" in grantee:
                target_type = "User"
                user_id = grantee["user"].get("id")
                user_obj = inventory["user_map"].get(user_id)
                user_name = getattr(user_obj, "name", None) or grantee["user"].get("name")
                target_name = user_name
                target_id = user_id
            elif "group" in grantee:
                target_type = "Group"
                group_id = grantee["group"].get("id")
                group_obj = inventory["group_map"].get(group_id)
                group_name = getattr(group_obj, "name", None) or grantee["group"].get("name")
                target_name = group_name
                target_id = group_id
            else:
                continue

            capabilities = grantee.get("capabilities", {}).get("capability", [])
            if isinstance(capabilities, dict):
                capabilities = [capabilities]

            for cap in capabilities:
                cap_name = cap.get("name")
                cap_mode = cap.get("mode")

                rows.append({
                    "content_type": content_type,
                    "content_id": getattr(content_obj, "id", None),
                    "content_name": getattr(content_obj, "name", None),
                    "project_id": getattr(content_obj, "project_id", None),
                    "project_name": getattr(project, "name", None) if project else getattr(content_obj, "name", None),
                    "owner_id": getattr(content_obj, "owner_id", None),
                    "owner_name": getattr(owner, "fullname", None) if owner else None,
                    "owner_username": getattr(owner, "name", None) if owner else None,
                    "permission_target_type": target_type,
                    "permission_target_id": target_id,
                    "permission_target_name": target_name,
                    "capability_name": cap_name,
                    "mode": cap_mode,
                    "is_all_users_group": str(target_name).strip().lower() == "all users",
                    "is_direct_user_permission": target_type == "User",
                    "is_high_privilege_capability": cap_name in {
                        "Write", "ProjectLeader", "ChangePermissions", "DownloadWorkbook",
                        "DownloadFullData", "Save", "WebAuthoring", "Overwrite"
                    },
                    "risk_level": "",
                    "risk_score": 0,
                    "finding_code": "",
                    "finding_message": "",
                    "recommended_action": "",
                })

        return rows
        
    def generate_permission_audit_report(
        self,
        project_names=None,
        include_projects=True,
        include_workbooks=True,
        include_datasources=True,
        flag_all_users=True,
        flag_direct_user=True,
        flag_non_inherited_workbooks=True,
        flag_non_inherited_datasources=True,
        flag_high_privilege=True,
        flag_change_permissions=True,
        flag_project_leader=True,
        broad_groups=None,
        forbidden_groups=None,
        approved_high_priv_groups=None,
        compare_to_baseline=False
    ):
        broad_groups = set([g.strip().lower() for g in (broad_groups or ["All Users"]) if str(g).strip()])
        forbidden_groups = set([g.strip().lower() for g in (forbidden_groups or ["All Users"]) if str(g).strip()])
        approved_high_priv_groups = set([g.strip().lower() for g in (approved_high_priv_groups or []) if str(g).strip()])

        inventory = self._build_permission_inventory(project_names=project_names)
        rows = []
        permission_fetch_errors = []

        token, site_id = self._rest_signin()
        try:
            if include_projects:
                for project in inventory["projects"]:
                    try:
                        logging.info(f"Fetching project permissions: {getattr(project, 'name', '')} ({getattr(project, 'id', '')})")
                        payload = self._get_project_permissions_rest(token, site_id, project.id)
                        rows.extend(self._normalize_grantee_capabilities("Project", project, payload, inventory))
                    except Exception as exc:
                        logging.exception(f"Failed to fetch project permissions for {getattr(project, 'name', '')} ({getattr(project, 'id', '')})")
                        permission_fetch_errors.append({
                            "content_type": "Project",
                            "content_name": getattr(project, "name", ""),
                            "content_id": getattr(project, "id", ""),
                            "error": str(exc),
                        })

            if include_workbooks:
                for workbook in inventory["workbooks"]:
                    try:
                        logging.info(f"Fetching workbook permissions: {getattr(workbook, 'name', '')} ({getattr(workbook, 'id', '')})")
                        payload = self._get_workbook_permissions_rest(token, site_id, workbook.id)
                        rows.extend(self._normalize_grantee_capabilities("Workbook", workbook, payload, inventory))
                    except Exception as exc:
                        logging.exception(f"Failed to fetch workbook permissions for {getattr(workbook, 'name', '')} ({getattr(workbook, 'id', '')})")
                        permission_fetch_errors.append({
                            "content_type": "Workbook",
                            "content_name": getattr(workbook, "name", ""),
                            "content_id": getattr(workbook, "id", ""),
                            "error": str(exc),
                        })

            if include_datasources:
                for datasource in inventory["datasources"]:
                    try:
                        logging.info(f"Fetching datasource permissions: {getattr(datasource, 'name', '')} ({getattr(datasource, 'id', '')})")
                        payload = self._get_datasource_permissions_rest(token, site_id, datasource.id)
                        rows.extend(self._normalize_grantee_capabilities("Data Source", datasource, payload, inventory))
                    except Exception as exc:
                        logging.exception(f"Failed to fetch datasource permissions for {getattr(datasource, 'name', '')} ({getattr(datasource, 'id', '')})")
                        permission_fetch_errors.append({
                            "content_type": "Data Source",
                            "content_name": getattr(datasource, "name", ""),
                            "content_id": getattr(datasource, "id", ""),
                            "error": str(exc),
                        })
        finally:
            self._rest_signout(token)

        df = pd.DataFrame(rows)

        required_columns = [
            "content_type",
            "content_id",
            "content_name",
            "project_id",
            "project_name",
            "owner_id",
            "owner_name",
            "owner_username",
            "permission_target_type",
            "permission_target_id",
            "permission_target_name",
            "capability_name",
            "mode",
            "is_all_users_group",
            "is_direct_user_permission",
            "is_high_privilege_capability",
            "risk_level",
            "risk_score",
            "finding_code",
            "finding_message",
            "recommended_action",
        ]

        for col in required_columns:
            if col not in df.columns:
                if col == "risk_score":
                    df[col] = 0
                elif col in (
                    "is_all_users_group",
                    "is_direct_user_permission",
                    "is_high_privilege_capability",
                ):
                    df[col] = False
                else:
                    df[col] = ""

        if df.empty:
            errors_df = pd.DataFrame(permission_fetch_errors) if permission_fetch_errors else pd.DataFrame(
                columns=["content_type", "content_name", "content_id", "error"]
            )

            return {
                "Summary": pd.DataFrame([{
                    "Projects Audited": len(inventory["projects"]) if include_projects else 0,
                    "Workbooks Audited": len(inventory["workbooks"]) if include_workbooks else 0,
                    "Data Sources Audited": len(inventory["datasources"]) if include_datasources else 0,
                    "High Findings": 0,
                    "Medium Findings": 0,
                    "Low Findings": 0,
                    "Total Findings": 0,
                    "API Errors": len(errors_df),
                }]),
                "Project Permissions": pd.DataFrame(columns=required_columns),
                "Workbook Permissions": pd.DataFrame(columns=required_columns),
                "Data Source Permissions": pd.DataFrame(columns=required_columns),
                "Exceptions": pd.DataFrame(columns=required_columns),
                "Group Risk Summary": pd.DataFrame(),
                "Direct User Access": pd.DataFrame(columns=required_columns),
                "API Errors": errors_df,
            }

        df["finding_code"] = df["finding_code"].fillna("")
        df["finding_message"] = df["finding_message"].fillna("")
        df["recommended_action"] = df["recommended_action"].fillna("")
        df["risk_level"] = df["risk_level"].fillna("")
        df["risk_score"] = pd.to_numeric(df["risk_score"], errors="coerce").fillna(0)

        def mark(mask, code, msg, score, action, severity=None):
            df.loc[mask, "finding_code"] = code
            df.loc[mask, "finding_message"] = msg
            df.loc[mask, "risk_score"] = df.loc[mask, "risk_score"] + score
            df.loc[mask, "recommended_action"] = action
            if severity:
                df.loc[mask, "risk_level"] = severity

        if flag_all_users:
            mask = (
                df["permission_target_type"].astype(str).eq("Group")
                & df["permission_target_name"].fillna("").astype(str).str.lower().isin(broad_groups | forbidden_groups)
                & df["mode"].astype(str).eq("Allow")
            )
            mark(
                mask,
                "ALL_USERS_PRESENT",
                "Broad group access detected.",
                50,
                "Remove broad group access or replace with approved Tableau group.",
                "High"
            )

        if flag_direct_user:
            mask = (
                df["is_direct_user_permission"].fillna(False)
                & df["mode"].astype(str).eq("Allow")
            )
            mark(
                mask,
                "DIRECT_USER_ACCESS",
                "Direct user permission detected.",
                20,
                "Replace direct user permissions with governed group access.",
                "Medium"
            )

        if flag_high_privilege:
            mask = (
                df["is_high_privilege_capability"].fillna(False)
                & df["mode"].astype(str).eq("Allow")
                & ~df["permission_target_name"].fillna("").astype(str).str.lower().isin(approved_high_priv_groups)
            )
            mark(
                mask,
                "HIGH_PRIVILEGE_ACCESS",
                "High-privilege capability granted.",
                25,
                "Review whether this grant is approved.",
                "Medium"
            )

        if flag_change_permissions:
            mask = (
                df["capability_name"].astype(str).eq("ChangePermissions")
                & df["mode"].astype(str).eq("Allow")
            )
            mark(
                mask,
                "CHANGE_PERMISSIONS_GRANTED",
                "Permission target can change permissions.",
                30,
                "Restrict ChangePermissions to approved admins/groups.",
                "High"
            )

        if flag_project_leader:
            mask = (
                df["capability_name"].astype(str).eq("ProjectLeader")
                & df["mode"].astype(str).eq("Allow")
            )
            mark(
                mask,
                "PROJECT_LEADER_GRANTED",
                "Project Leader-like access detected.",
                25,
                "Validate project leader assignment.",
                "Medium"
            )

        if flag_non_inherited_workbooks:
            mask = (
                df["content_type"].astype(str).eq("Workbook")
                & df["mode"].astype(str).eq("Allow")
                & df["is_direct_user_permission"].fillna(False)
            )
            mark(
                mask,
                "WORKBOOK_CUSTOM_PERMISSION",
                "Workbook may have custom/non-inherited permissions.",
                15,
                "Review workbook permissions against project inheritance.",
                "Medium"
            )

        if flag_non_inherited_datasources:
            mask = (
                df["content_type"].astype(str).eq("Data Source")
                & df["mode"].astype(str).eq("Allow")
                & df["is_direct_user_permission"].fillna(False)
            )
            mark(
                mask,
                "DATASOURCE_CUSTOM_PERMISSION",
                "Data source may have custom/non-inherited permissions.",
                15,
                "Review data source permissions against project inheritance.",
                "Medium"
            )

        # Workbook access exists but project access does not
        required_compare_cols = [
            "content_type",
            "content_id",
            "content_name",
            "project_id",
            "project_name",
            "permission_target_type",
            "permission_target_id",
            "permission_target_name",
            "capability_name",
            "mode",
        ]

        if all(col in df.columns for col in required_compare_cols):
            workbook_allow_df = df[
                (df["content_type"].astype(str) == "Workbook") &
                (df["mode"].astype(str) == "Allow")
            ].copy()

            project_allow_df = df[
                (df["content_type"].astype(str) == "Project") &
                (df["mode"].astype(str) == "Allow")
            ].copy()

            if not workbook_allow_df.empty and not project_allow_df.empty:
                workbook_compare = workbook_allow_df[
                    [
                        "content_id",
                        "content_name",
                        "project_id",
                        "project_name",
                        "permission_target_type",
                        "permission_target_id",
                        "permission_target_name",
                        "capability_name",
                        "mode"
                    ]
                ].copy()

                project_compare = project_allow_df[
                    [
                        "content_id",
                        "content_name",
                        "permission_target_type",
                        "permission_target_id",
                        "permission_target_name",
                        "capability_name",
                        "mode"
                    ]
                ].copy()

                project_compare = project_compare.rename(columns={
                    "content_id": "parent_project_id",
                    "content_name": "parent_project_name",
                    "permission_target_type": "project_permission_target_type",
                    "permission_target_id": "project_permission_target_id",
                    "permission_target_name": "project_permission_target_name",
                    "capability_name": "project_capability_name",
                    "mode": "project_mode"
                })

                workbook_vs_project = workbook_compare.merge(
                    project_compare,
                    how="left",
                    left_on=[
                        "project_id",
                        "permission_target_type",
                        "permission_target_id",
                        "capability_name",
                        "mode"
                    ],
                    right_on=[
                        "parent_project_id",
                        "project_permission_target_type",
                        "project_permission_target_id",
                        "project_capability_name",
                        "project_mode"
                    ]
                )

                workbook_missing_project_access = workbook_vs_project["parent_project_id"].isna()

                if workbook_missing_project_access.any():
                    mismatch_keys = workbook_vs_project.loc[
                        workbook_missing_project_access,
                        [
                            "content_id",
                            "permission_target_type",
                            "permission_target_id",
                            "capability_name",
                            "mode"
                        ]
                    ].drop_duplicates()

                    mismatch_df = mismatch_keys.assign(_flag_workbook_not_project=True)

                    df = df.merge(
                        mismatch_df,
                        how="left",
                        on=[
                            "content_id",
                            "permission_target_type",
                            "permission_target_id",
                            "capability_name",
                            "mode"
                        ]
                    )

                    df["_flag_workbook_not_project"] = df["_flag_workbook_not_project"].fillna(False)

                    high_caps = {
                        "Write",
                        "ChangePermissions",
                        "ProjectLeader",
                        "DownloadWorkbook",
                        "DownloadFullData",
                        "Overwrite",
                        "WebAuthoring",
                        "Save"
                    }

                    high_mask = (
                        df["content_type"].astype(str).eq("Workbook")
                        & df["_flag_workbook_not_project"].eq(True)
                        & df["capability_name"].isin(high_caps)
                    )

                    medium_mask = (
                        df["content_type"].astype(str).eq("Workbook")
                        & df["_flag_workbook_not_project"].eq(True)
                        & ~df["capability_name"].isin(high_caps)
                    )

                    mark(
                        high_mask,
                        "WORKBOOK_ACCESS_NOT_IN_PROJECT",
                        "Workbook access exists but equivalent parent project access was not found.",
                        35,
                        "Review workbook custom permissions and align them with the parent project if not intended.",
                        "High"
                    )

                    mark(
                        medium_mask,
                        "WORKBOOK_ACCESS_NOT_IN_PROJECT",
                        "Workbook access exists but equivalent parent project access was not found.",
                        20,
                        "Review workbook custom permissions and align them with the parent project if not intended.",
                        "Medium"
                    )

                    df = df.drop(columns=["_flag_workbook_not_project"], errors="ignore")

        df.loc[(df["risk_level"] == "") & (df["risk_score"] >= 70), "risk_level"] = "High"
        df.loc[(df["risk_level"] == "") & (df["risk_score"].between(35, 69)), "risk_level"] = "Medium"
        df.loc[(df["risk_level"] == "") & (df["risk_score"] > 0), "risk_level"] = "Low"

        exceptions = df[df["risk_score"] > 0].copy()

        summary = pd.DataFrame([{
            "Projects Audited": len(inventory["projects"]) if include_projects else 0,
            "Workbooks Audited": len(inventory["workbooks"]) if include_workbooks else 0,
            "Data Sources Audited": len(inventory["datasources"]) if include_datasources else 0,
            "High Findings": int((exceptions["risk_level"] == "High").sum()) if not exceptions.empty else 0,
            "Medium Findings": int((exceptions["risk_level"] == "Medium").sum()) if not exceptions.empty else 0,
            "Low Findings": int((exceptions["risk_level"] == "Low").sum()) if not exceptions.empty else 0,
            "Total Findings": len(exceptions),
            "API Errors": len(permission_fetch_errors),
        }])

        project_df = df[df["content_type"].astype(str) == "Project"].copy()
        workbook_df = df[df["content_type"].astype(str) == "Workbook"].copy()
        datasource_df = df[df["content_type"].astype(str) == "Data Source"].copy()

        group_risk = (
            exceptions[exceptions["permission_target_type"].astype(str) == "Group"]
            .groupby(["permission_target_name", "risk_level"], dropna=False)
            .size()
            .reset_index(name="finding_count")
            if not exceptions.empty else pd.DataFrame()
        )

        user_direct = exceptions[exceptions["is_direct_user_permission"].fillna(False)].copy()

        errors_df = pd.DataFrame(permission_fetch_errors) if permission_fetch_errors else pd.DataFrame(
            columns=["content_type", "content_name", "content_id", "error"]
        )

        return {
            "Summary": summary,
            "Project Permissions": project_df,
            "Workbook Permissions": workbook_df,
            "Data Source Permissions": datasource_df,
            "Exceptions": exceptions,
            "Group Risk Summary": group_risk,
            "Direct User Access": user_direct,
            "API Errors": errors_df,
        }
    
    def get_permission_audit_summary(self, **kwargs):
        reports = self.generate_permission_audit_report(**kwargs)
        summary_df = reports["Summary"]
        if summary_df.empty:
            return {
                "projects_audited": 0,
                "workbooks_audited": 0,
                "datasources_audited": 0,
                "high_findings": 0,
                "medium_findings": 0,
                "low_findings": 0,
                "total_findings": 0,
            }

        row = summary_df.iloc[0].to_dict()
        return {
            "projects_audited": int(row.get("Projects Audited", 0)),
            "workbooks_audited": int(row.get("Workbooks Audited", 0)),
            "datasources_audited": int(row.get("Data Sources Audited", 0)),
            "high_findings": int(row.get("High Findings", 0)),
            "medium_findings": int(row.get("Medium Findings", 0)),
            "low_findings": int(row.get("Low Findings", 0)),
            "total_findings": int(row.get("Total Findings", 0)),
        }
    
    def bulk_add_users(self, usernames, site_role='Viewer', group_names=None):
        group_names = set(group_names or [])
        results = {
            "added": [],
            "failed": [],
            "skipped": [],
        }

        with self.signin() as server:
            req = tsc.RequestOptions()
            req.pagesize = 1000
            existing_users = list(tsc.Pager(server.users, req))
            existing_usernames = {(u.name or "").strip().lower() for u in existing_users}

            groups = list(tsc.Pager(server.groups))
            groups_by_name = {g.name: g for g in groups}

            for username in usernames:
                username = (username or "").strip()
                if not username:
                    results["skipped"].append({
                        "username": "",
                        "reason": "Blank NTLogin"
                    })
                    continue

                if username.lower() in existing_usernames:
                    results["skipped"].append({
                        "username": username,
                        "reason": "User already exists"
                    })
                    continue

                try:
                    new_user = tsc.UserItem(name=username, site_role=site_role)
                    created_user = server.users.add(new_user)
                    created_user = server.users.get_by_id(created_user.id)

                    if created_user.site_role == 'Unlicensed':
                        server.users.remove(created_user.id)
                        results["failed"].append({
                            "username": username,
                            "reason": "No licenses available"
                        })
                        continue

                    for group_name in group_names:
                        group = groups_by_name.get(group_name)
                        if group:
                            server.groups.add_user(group, created_user.id)

                    results["added"].append(username)
                    existing_usernames.add(username.lower())

                except Exception as exc:
                    results["failed"].append({
                        "username": username,
                        "reason": str(exc)
                    })

        return results
        
    def get_subscriptions_inventory(self):
        with self.signin() as server:
            subscriptions = self._get_paged_items(server.subscriptions, 1000)

            user_req = tsc.RequestOptions()
            user_req.pagesize = 1000
            users = list(tsc.Pager(server.users, user_req))
            user_map = {user.id: user for user in users}

            workbook_req = tsc.RequestOptions()
            workbook_req.pagesize = 1000
            workbooks = list(tsc.Pager(server.workbooks, workbook_req))
            workbook_map = {wb.id: wb for wb in workbooks}

            project_req = tsc.RequestOptions()
            project_req.pagesize = 1000
            projects = list(tsc.Pager(server.projects, project_req))
            project_map = {project.id: project for project in projects}

            view_target_ids = {
                getattr(getattr(sub, "target", None), "id", "") or ""
                for sub in subscriptions
                if str(getattr(getattr(sub, "target", None), "type", "")).lower() == "view"
            }
            view_target_ids.discard("")

            view_name_map = {}

            if view_target_ids:
                unresolved_view_ids = set(view_target_ids)

                for workbook in workbooks:
                    if not unresolved_view_ids:
                        break

                    try:
                        server.workbooks.populate_views(workbook)
                        for view in getattr(workbook, "views", []) or []:
                            view_id = getattr(view, "id", "") or ""
                            if view_id in unresolved_view_ids:
                                view_name_map[view_id] = {
                                    "view_name": getattr(view, "name", "") or "",
                                    "workbook_id": getattr(workbook, "id", "") or "",
                                    "workbook_name": getattr(workbook, "name", "") or "",
                                    "project_id": getattr(workbook, "project_id", "") or "",
                                }
                                unresolved_view_ids.discard(view_id)
                    except Exception:
                        logging.exception(
                            f"Failed to populate views for workbook {getattr(workbook, 'name', '')} ({getattr(workbook, 'id', '')})"
                        )

            rows = []

            for subscription in subscriptions:
                subscription_id = getattr(subscription, "id", "") or ""
                subject = getattr(subscription, "subject", "") or ""
                owner_id = getattr(subscription, "user_id", "") or ""
                owner = user_map.get(owner_id)

                target = getattr(subscription, "target", None)
                content_id = getattr(target, "id", "") if target else ""
                content_type_raw = getattr(target, "type", "") if target else ""
                content_type = (content_type_raw or "Unknown").title()

                content_name = ""
                workbook_name = ""
                view_name = ""
                project_name = ""
                warning = ""
                is_suspicious = False

                if str(content_type_raw).lower() == "workbook":
                    workbook = workbook_map.get(content_id)
                    if workbook:
                        content_name = getattr(workbook, "name", "") or ""
                        workbook_name = content_name
                        project = project_map.get(getattr(workbook, "project_id", None))
                        project_name = getattr(project, "name", "") if project else ""
                    else:
                        content_name = "Missing Workbook"
                        warning = "Subscription target workbook was not found."
                        is_suspicious = True

                elif str(content_type_raw).lower() == "view":
                    view_info = view_name_map.get(content_id)
                    if view_info:
                        view_name = view_info.get("view_name", "")
                        workbook_name = view_info.get("workbook_name", "")
                        content_name = view_name or workbook_name or f"View ID: {content_id}"
                        project = project_map.get(view_info.get("project_id"))
                        project_name = getattr(project, "name", "") if project else ""
                    else:
                        content_name = f"View ID: {content_id}"
                        warning = "View name was not resolved."
                        is_suspicious = True

                else:
                    content_name = "Unknown Content Type"
                    warning = f"Unsupported or unknown subscription target type: {content_type_raw}"
                    is_suspicious = True

                if not owner:
                    if warning:
                        warning += " "
                    warning += "Subscription owner was not found."
                    is_suspicious = True

                schedule_id = getattr(subscription, "schedule_id", "") or ""
                schedule_name = getattr(subscription, "schedule_name", "") or ""
                if not schedule_name:
                    schedule_name = "Unknown"

                status = "Active"
                if is_suspicious:
                    status = "Suspicious"

                rows.append({
                    "subscription_id": subscription_id,
                    "subject": subject,
                    "owner_id": owner_id,
                    "owner_name": getattr(owner, "fullname", "") if owner else "",
                    "owner_username": getattr(owner, "name", "") if owner else "",
                    "owner_email": getattr(owner, "email", "") if owner else "",
                    "owner_site_role": getattr(owner, "site_role", "") if owner else "",
                    "content_id": content_id,
                    "content_type": content_type,
                    "content_name": content_name,
                    "workbook_name": workbook_name,
                    "view_name": view_name,
                    "project_name": project_name,
                    "schedule_id": schedule_id,
                    "schedule_name": schedule_name,
                    "status": status,
                    "is_suspicious": is_suspicious,
                    "warning": warning,
                })

            return sorted(
                rows,
                key=lambda item: (
                    str(item.get("owner_name", "")).lower(),
                    str(item.get("subject", "")).lower(),
                    str(item.get("subscription_id", "")).lower(),
                )
            )

    def delete_subscription(self, subscription_id):
        if not subscription_id:
            raise RuntimeError("Subscription ID is required.")

        with self.signin() as server:
            try:
                server.subscriptions.delete(subscription_id)
            except Exception as exc:
                raise RuntimeError(f"Failed to delete subscription {subscription_id}: {exc}")

    def generate_subscriptions_report(self):
        inventory = self.get_subscriptions_inventory()

        if not inventory:
            return pd.DataFrame(columns=[
                "Subscription ID",
                "Subscription Subject",
                "Subscription Owner ID",
                "Subscription Owner Display Name",
                "Subscription Owner Username",
                "Subscription Owner Email Address",
                "Subscription Owner Site Role",
                "Subscription Content ID",
                "Subscription Content Type",
                "Subscription Content Name",
                "Workbook Name",
                "View Name",
                "Project Name",
                "Schedule ID",
                "Schedule Name",
                "Status",
                "Is Suspicious",
                "Warning",
            ])

        return pd.DataFrame([
            {
                "Subscription ID": item.get("subscription_id", ""),
                "Subscription Subject": item.get("subject", ""),
                "Subscription Owner ID": item.get("owner_id", ""),
                "Subscription Owner Display Name": item.get("owner_name", ""),
                "Subscription Owner Username": item.get("owner_username", ""),
                "Subscription Owner Email Address": item.get("owner_email", ""),
                "Subscription Owner Site Role": item.get("owner_site_role", ""),
                "Subscription Content ID": item.get("content_id", ""),
                "Subscription Content Type": item.get("content_type", ""),
                "Subscription Content Name": item.get("content_name", ""),
                "Workbook Name": item.get("workbook_name", ""),
                "View Name": item.get("view_name", ""),
                "Project Name": item.get("project_name", ""),
                "Schedule ID": item.get("schedule_id", ""),
                "Schedule Name": item.get("schedule_name", ""),
                "Status": item.get("status", ""),
                "Is Suspicious": item.get("is_suspicious", False),
                "Warning": item.get("warning", ""),
            }
            for item in inventory
        ])
        
    def _delete_workbook_group_permission_rest(self, token, site_id, workbook_id, group_id, capability_name, mode):
        url = (
            f"{self.server_url}/api/{self.server.version}/sites/{site_id}/workbooks/"
            f"{workbook_id}/permissions/groups/{group_id}/{capability_name}/{mode}"
        )

        resp = requests.delete(
            url,
            headers={"X-Tableau-Auth": token, "Accept": "application/json"},
            timeout=60
        )
        resp.raise_for_status()


    def remove_group_permissions_from_content(self, group_name, ignore_projects=None, ignore_workbooks=None, progress_callback=None):
        ignore_projects = set(ignore_projects or [])
        ignore_workbooks = set(ignore_workbooks or [])

        def update(msg):
            if progress_callback:
                progress_callback(msg)

        with self.signin() as server:
            projects = list(tsc.Pager(server.projects))
            workbooks = list(tsc.Pager(server.workbooks))
            groups = list(tsc.Pager(server.groups))

        project_map = {p.id: p for p in projects}
        target_group = next(
            (g for g in groups if (g.name or "").strip().lower() == group_name.strip().lower()),
            None
        )

        if not target_group:
            raise RuntimeError(f"Group not found: {group_name}")

        token, site_id = self._rest_signin()
        changes = []

        try:
            for workbook in workbooks:
                workbook_name = getattr(workbook, "name", "") or ""
                project = project_map.get(getattr(workbook, "project_id", None))
                project_name = getattr(project, "name", "") if project else ""

                if project_name in ignore_projects:
                    continue

                if workbook_name in ignore_workbooks:
                    continue

                update(f"Checking workbook permissions: {workbook_name}")

                try:
                    payload = self._get_workbook_permissions_rest(token, site_id, workbook.id)
                    grantee_caps = payload.get("permissions", {}).get("granteeCapabilities", []) or []
                    if isinstance(grantee_caps, dict):
                        grantee_caps = [grantee_caps]

                    for grantee in grantee_caps:
                        group_data = grantee.get("group")
                        if not group_data:
                            continue

                        grantee_group_id = group_data.get("id", "")
                        grantee_group_name = group_data.get("name", "")

                        if str(grantee_group_id).strip() != str(target_group.id).strip():
                            continue

                        capabilities = grantee.get("capabilities", {}).get("capability", [])
                        if isinstance(capabilities, dict):
                            capabilities = [capabilities]

                        for cap in capabilities:
                            capability_name = cap.get("name", "")
                            mode = cap.get("mode", "")

                            self._delete_workbook_group_permission_rest(
                                token=token,
                                site_id=site_id,
                                workbook_id=workbook.id,
                                group_id=target_group.id,
                                capability_name=capability_name,
                                mode=mode
                            )

                            changes.append({
                                "content_type": "Workbook",
                                "project_name": project_name,
                                "content_name": workbook_name,
                                "content_id": workbook.id,
                                "group_name": grantee_group_name,
                                "group_id": grantee_group_id,
                                "capability_name": capability_name,
                                "mode": mode,
                                "action": "Removed permission"
                            })

                except Exception as exc:
                    changes.append({
                        "content_type": "Workbook",
                        "project_name": project_name,
                        "content_name": workbook_name,
                        "content_id": getattr(workbook, "id", ""),
                        "group_name": group_name,
                        "group_id": getattr(target_group, "id", ""),
                        "capability_name": "",
                        "mode": "",
                        "action": f"Error: {exc}"
                    })

        finally:
            self._rest_signout(token)

        documents = os.path.join(os.environ["USERPROFILE"], "Documents")
        export_path = os.path.join(documents, "Tableau Server - Removed Group Permissions.xlsx")

        df = pd.DataFrame(changes)
        if df.empty:
            df = pd.DataFrame(columns=[
                "content_type",
                "project_name",
                "content_name",
                "content_id",
                "group_name",
                "group_id",
                "capability_name",
                "mode",
                "action",
            ])

        with pd.ExcelWriter(export_path) as writer:
            df.to_excel(writer, sheet_name="Changes", index=False)

        return {
            "changes": changes,
            "export_path": export_path,
        }
            
    def _export_group_permission_changes(self, rows, filename):
        documents = os.path.join(os.environ["USERPROFILE"], "Documents")
        path = os.path.join(documents, filename)

        df = pd.DataFrame(rows)
        if df.empty:
            df = pd.DataFrame(columns=[
                "content_type",
                "project_name",
                "content_name",
                "content_id",
                "group_name",
                "group_id",
                "capability_name",
                "mode",
                "action",
            ])

        with pd.ExcelWriter(path) as writer:
            df.to_excel(writer, sheet_name="Changes", index=False)

        return path
            
    def preview_remove_group_permissions_from_content(self, group_name, ignore_projects=None, ignore_workbooks=None, progress_callback=None):
        ignore_projects = set(ignore_projects or [])
        ignore_workbooks = set(ignore_workbooks or [])

        def update(msg):
            if progress_callback:
                progress_callback(msg)

        with self.signin() as server:
            projects = list(tsc.Pager(server.projects))
            workbooks = list(tsc.Pager(server.workbooks))
            groups = list(tsc.Pager(server.groups))

        project_map = {p.id: p for p in projects}
        target_group = next(
            (g for g in groups if (g.name or "").strip().lower() == group_name.strip().lower()),
            None
        )

        if not target_group:
            raise RuntimeError(f"Group not found: {group_name}")

        token, site_id = self._rest_signin()
        changes = []

        try:
            # Preview project permissions
            for project in projects:
                project_name = getattr(project, "name", "") or ""

                if project_name in ignore_projects:
                    continue

                update(f"Previewing project permissions: {project_name}")

                payload = self._get_project_permissions_rest(token, site_id, project.id)
                grantee_caps = payload.get("permissions", {}).get("granteeCapabilities", []) or []
                if isinstance(grantee_caps, dict):
                    grantee_caps = [grantee_caps]

                for grantee in grantee_caps:
                    group_data = grantee.get("group")
                    if not group_data:
                        continue

                    grantee_group_id = group_data.get("id", "")
                    grantee_group_name = group_data.get("name", "")

                    if str(grantee_group_id).strip() != str(target_group.id).strip():
                        continue

                    capabilities = grantee.get("capabilities", {}).get("capability", [])
                    if isinstance(capabilities, dict):
                        capabilities = [capabilities]

                    for cap in capabilities:
                        changes.append({
                            "content_type": "Project",
                            "project_name": project_name,
                            "content_name": project_name,
                            "content_id": project.id,
                            "group_name": grantee_group_name,
                            "group_id": grantee_group_id,
                            "capability_name": cap.get("name", ""),
                            "mode": cap.get("mode", ""),
                            "action": "Preview only"
                        })

            # Preview workbook permissions
            for workbook in workbooks:
                workbook_name = getattr(workbook, "name", "") or ""
                project = project_map.get(getattr(workbook, "project_id", None))
                project_name = getattr(project, "name", "") if project else ""

                if project_name in ignore_projects:
                    continue

                if workbook_name in ignore_workbooks:
                    continue

                update(f"Previewing workbook permissions: {workbook_name}")

                payload = self._get_workbook_permissions_rest(token, site_id, workbook.id)
                grantee_caps = payload.get("permissions", {}).get("granteeCapabilities", []) or []
                if isinstance(grantee_caps, dict):
                    grantee_caps = [grantee_caps]

                for grantee in grantee_caps:
                    group_data = grantee.get("group")
                    if not group_data:
                        continue

                    grantee_group_id = group_data.get("id", "")
                    grantee_group_name = group_data.get("name", "")

                    if str(grantee_group_id).strip() != str(target_group.id).strip():
                        continue

                    capabilities = grantee.get("capabilities", {}).get("capability", [])
                    if isinstance(capabilities, dict):
                        capabilities = [capabilities]

                    for cap in capabilities:
                        changes.append({
                            "content_type": "Workbook",
                            "project_name": project_name,
                            "content_name": workbook_name,
                            "content_id": workbook.id,
                            "group_name": grantee_group_name,
                            "group_id": grantee_group_id,
                            "capability_name": cap.get("name", ""),
                            "mode": cap.get("mode", ""),
                            "action": "Preview only"
                        })
        finally:
            self._rest_signout(token)

        export_path = self._export_group_permission_changes(
            changes,
            "Tableau Server - Remove Group Permission Preview.xlsx"
        )

        return {
            "changes": changes,
            "export_path": export_path,
        }
        
    def _delete_workbook_group_permission_rest(self, token, site_id, workbook_id, group_id, capability_name, mode):
        url = (
            f"{self.server_url}/api/{self.server.version}/sites/{site_id}/workbooks/"
            f"{workbook_id}/permissions/groups/{group_id}/{capability_name}/{mode}"
        )

        resp = requests.delete(
            url,
            headers={"X-Tableau-Auth": token, "Accept": "application/json"},
            timeout=60
        )
        resp.raise_for_status()


    def apply_remove_group_permissions_from_content(self, preview_rows, group_name, progress_callback=None):
        preview_rows = list(preview_rows or [])

        if not preview_rows:
            raise RuntimeError("No preview rows were provided to apply.")

        def update(msg):
            if progress_callback:
                progress_callback(msg)

        token, site_id = self._rest_signin()
        applied = []

        try:
            for row in preview_rows:
                content_type = row.get("content_type", "")
                content_name = row.get("content_name", "")

                update(f"Removing permission from {content_type.lower()}: {content_name}")

                try:
                    if content_type == "Project":
                        self._delete_project_group_permission_rest(
                            token=token,
                            site_id=site_id,
                            project_id=row["content_id"],
                            group_id=row["group_id"],
                            capability_name=row["capability_name"],
                            mode=row["mode"]
                        )
                    elif content_type == "Workbook":
                        self._delete_workbook_group_permission_rest(
                            token=token,
                            site_id=site_id,
                            workbook_id=row["content_id"],
                            group_id=row["group_id"],
                            capability_name=row["capability_name"],
                            mode=row["mode"]
                        )
                    else:
                        applied.append({
                            **row,
                            "action": f"Skipped unsupported content type: {content_type}"
                        })
                        continue

                    applied.append({
                        **row,
                        "action": "Removed permission"
                    })

                except Exception as exc:
                    applied.append({
                        **row,
                        "action": f"Error: {exc}"
                    })
        finally:
            self._rest_signout(token)

        export_path = self._export_group_permission_changes(
            applied,
            "Tableau Server - Removed Group Permissions.xlsx"
        )

        return {
            "changes": applied,
            "export_path": export_path,
        }
        
    def _delete_project_group_permission_rest(self, token, site_id, project_id, group_id, capability_name, mode):
        url = (
            f"{self.server_url}/api/{self.server.version}/sites/{site_id}/projects/"
            f"{project_id}/permissions/groups/{group_id}/{capability_name}/{mode}"
        )

        resp = requests.delete(
            url,
            headers={"X-Tableau-Auth": token, "Accept": "application/json"},
            timeout=60
        )
        resp.raise_for_status()


    def _delete_workbook_group_permission_rest(self, token, site_id, workbook_id, group_id, capability_name, mode):
        url = (
            f"{self.server_url}/api/{self.server.version}/sites/{site_id}/workbooks/"
            f"{workbook_id}/permissions/groups/{group_id}/{capability_name}/{mode}"
        )

        resp = requests.delete(
            url,
            headers={"X-Tableau-Auth": token, "Accept": "application/json"},
            timeout=60
        )
        resp.raise_for_status()
        
    def _build_sql_connection_string(self, sql_server, sql_username, sql_password, sql_database="master", sql_driver="ODBC Driver 17 for SQL Server"):
        return (
            f"DRIVER={{{sql_driver}}};"
            f"SERVER={sql_server};"
            f"DATABASE={sql_database};"
            f"UID={sql_username};"
            f"PWD={sql_password};"
            "TrustServerCertificate=yes;"
        )


    def _load_recently_termed_users_from_sql(
        self,
        sql_server,
        sql_username,
        sql_password,
        sql_database="master",
        sql_driver="ODBC Driver 17 for SQL Server",
        lookback_days=30
    ):
        query = f"""
        Select distinct SAMACCOUNTNAME as NTLOGIN
        From Employee.UXID.Enterprise_Roster
        Where Termdate > getdate()-{int(lookback_days)}
        """

        conn_str = self._build_sql_connection_string(
            sql_server=sql_server,
            sql_username=sql_username,
            sql_password=sql_password,
            sql_database=sql_database,
            sql_driver=sql_driver
        )

        users = set()

        with pyodbc.connect(conn_str) as conn:
            cursor = conn.cursor()
            cursor.execute(query)

            for row in cursor.fetchall():
                ntlogin = (getattr(row, "NTLOGIN", None) or "").strip()
                if ntlogin:
                    users.add(ntlogin.lower())

        return users


    def _export_termed_user_changes(self, rows, filename):
        documents = os.path.join(os.environ["USERPROFILE"], "Documents")
        path = os.path.join(documents, filename)

        df = pd.DataFrame(rows)
        if df.empty:
            df = pd.DataFrame(columns=[
                "ntlogin",
                "tableau_user_id",
                "site_role",
                "action",
                "status",
                "message",
            ])

        with pd.ExcelWriter(path) as writer:
            df.to_excel(writer, sheet_name="Changes", index=False)

        return path


    def preview_remove_termed_users(
        self,
        sql_server,
        sql_username,
        sql_password,
        sql_database="master",
        sql_driver="ODBC Driver 17 for SQL Server",
        lookback_days=30,
        exclude_server_roles=True,
        progress_callback=None
    ):
        def update(msg):
            if progress_callback:
                progress_callback(msg)

        update("Loading recently termed users from SQL Server...")
        termed_users = self._load_recently_termed_users_from_sql(
            sql_server=sql_server,
            sql_username=sql_username,
            sql_password=sql_password,
            sql_database=sql_database,
            sql_driver=sql_driver,
            lookback_days=lookback_days
        )

        rows = []

        update("Loading Tableau users...")
        with self.signin() as server:
            req = tsc.RequestOptions()
            req.pagesize = 1000
            tableau_users = list(tsc.Pager(server.users, req))

            for user in tableau_users:
                site_role = getattr(user, "site_role", "") or ""

                if exclude_server_roles and "Server" in site_role:
                    continue

                ntlogin = (getattr(user, "name", "") or "").strip().lower()
                if ntlogin not in termed_users:
                    continue

                rows.append({
                    "ntlogin": getattr(user, "name", "") or "",
                    "tableau_user_id": getattr(user, "id", "") or "",
                    "site_role": site_role,
                    "action": "would_delete",
                    "status": "success",
                    "message": "",
                })

        export_path = self._export_termed_user_changes(
            rows,
            "Tableau Server - Remove Termed Users Preview.xlsx"
        )

        return {
            "changes": rows,
            "export_path": export_path,
        }


    def apply_remove_termed_users(self, preview_rows, progress_callback=None):
        preview_rows = list(preview_rows or [])
        if not preview_rows:
            raise RuntimeError("No preview rows were provided to apply.")

        def update(msg):
            if progress_callback:
                progress_callback(msg)

        results = []

        for row in preview_rows:
            ntlogin = row.get("ntlogin", "")
            tableau_user_id = row.get("tableau_user_id", "")
            site_role = row.get("site_role", "")

            result_row = {
                "ntlogin": ntlogin,
                "tableau_user_id": tableau_user_id,
                "site_role": site_role,
                "action": "deleted",
                "status": "success",
                "message": "",
            }

            try:
                update(f"Removing Tableau user: {ntlogin}")
                self.remove_user(tableau_user_id)
            except Exception as exc:
                result_row["action"] = "error"
                result_row["status"] = "failed"
                result_row["message"] = str(exc)

            results.append(result_row)

        export_path = self._export_termed_user_changes(
            results,
            "Tableau Server - Removed Termed Users.xlsx"
        )

        return {
            "changes": results,
            "export_path": export_path,
        }
        
    def get_failed_jobs_last_24_hours(self, hours=24, progress_callback=None):
        from datetime import datetime, timedelta, timezone

        def update(msg):
            if progress_callback:
                progress_callback(msg)

        def parse_tableau_datetime(value):
            if not value:
                return None

            try:
                value = str(value).strip()
                if value.endswith("Z"):
                    value = value[:-1] + "+00:00"

                dt = datetime.fromisoformat(value)

                if dt.tzinfo is None:
                    dt = dt.replace(tzinfo=timezone.utc)

                return dt.astimezone(timezone.utc)
            except Exception:
                return None

        def is_failed_job(job):
            status = str(
                job.get("status")
                or job.get("jobStatus")
                or job.get("state")
                or ""
            ).strip().lower()

            finish_code = str(
                job.get("finishCode")
                or job.get("finish_code")
                or ""
            ).strip().lower()

            # Tableau commonly represents failed background jobs by status,
            # finish code, or both depending on endpoint/API version.
            failed_statuses = {
                "failed",
                "failure",
                "error",
                "cancelled",
                "canceled",
            }

            failed_finish_codes = {
                "1",
                "failed",
                "failure",
                "error",
            }

            return status in failed_statuses or finish_code in failed_finish_codes

        def normalize_job(job):
            created_at = (
                job.get("createdAt")
                or job.get("created_at")
                or job.get("created")
                or ""
            )

            started_at = (
                job.get("startedAt")
                or job.get("started_at")
                or job.get("started")
                or ""
            )

            ended_at = (
                job.get("endedAt")
                or job.get("completedAt")
                or job.get("finishedAt")
                or job.get("ended_at")
                or job.get("completed_at")
                or job.get("finished_at")
                or ""
            )

            job_time = (
                parse_tableau_datetime(ended_at)
                or parse_tableau_datetime(started_at)
                or parse_tableau_datetime(created_at)
            )

            return {
                "job_id": job.get("id", ""),
                "job_type": job.get("jobType") or job.get("type") or job.get("job_type") or "",
                "status": job.get("status") or job.get("jobStatus") or job.get("state") or "",
                "finish_code": job.get("finishCode") or job.get("finish_code") or "",
                "created_at": created_at,
                "started_at": started_at,
                "ended_at": ended_at,
                "title": job.get("title") or job.get("name") or "",
                "notes": job.get("notes") or job.get("message") or job.get("errorMessage") or "",
                "progress": job.get("progress") or "",
                "_job_time": job_time,
            }

        update("Checking Tableau job failures from the last 24 hours...")

        signin_url = f"{self.server_url}/api/{self.server.version}/auth/signin"
        signin_payload = {
            "credentials": {
                "personalAccessTokenName": self.token_name,
                "personalAccessTokenSecret": self.token_value,
                "site": {
                    "contentUrl": self.site_content_url
                }
            }
        }

        headers = {
            "Content-Type": "application/json",
            "Accept": "application/json"
        }

        response = requests.post(signin_url, json=signin_payload, headers=headers)
        response.raise_for_status()

        data = response.json()
        token = data["credentials"]["token"]
        site_id = data["credentials"]["site"]["id"]

        try:
            cutoff = datetime.now(timezone.utc) - timedelta(hours=hours)
            failed_jobs = []

            page_number = 1
            page_size = 1000

            while True:
                url = (
                    f"{self.server_url}/api/{self.server.version}/sites/{site_id}/jobs"
                    f"?pageSize={page_size}&pageNumber={page_number}"
                )

                resp = requests.get(
                    url,
                    headers={
                        "X-Tableau-Auth": token,
                        "Accept": "application/json"
                    },
                    timeout=120
                )
                resp.raise_for_status()

                payload = resp.json()

                jobs = (
                    payload.get("backgroundJobs", {}).get("backgroundJob")
                    or payload.get("jobs", {}).get("job")
                    or payload.get("jobs", [])
                    or []
                )

                if isinstance(jobs, dict):
                    jobs = [jobs]

                if not jobs:
                    break

                for job in jobs:
                    normalized = normalize_job(job)
                    job_time = normalized.get("_job_time")

                    if job_time and job_time < cutoff:
                        continue

                    if is_failed_job(job):
                        normalized.pop("_job_time", None)
                        failed_jobs.append(normalized)

                pagination = payload.get("pagination", {})
                total_available = int(pagination.get("totalAvailable", 0) or 0)

                if not total_available:
                    break

                if page_number * page_size >= total_available:
                    break

                page_number += 1

            failed_jobs.sort(
                key=lambda row: row.get("ended_at") or row.get("started_at") or row.get("created_at") or "",
                reverse=True
            )

            return failed_jobs

        finally:
            try:
                signout_url = f"{self.server_url}/api/{self.server.version}/auth/signout"
                requests.post(signout_url, headers={"X-Tableau-Auth": token})
            except Exception:
                pass