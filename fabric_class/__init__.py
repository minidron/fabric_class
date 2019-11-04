import inspect
import os
import sys
import time

from fabric.api import env, get, lcd, local, prefix, run, sudo
from fabric.contrib.files import exists


def add_class_methods_as_functions(instance, module_name):
    """
    Utility to take the methods with prefix 'fab_' of the class instance,
    and add them as functions to a module `module_name`, so that Fabric
    can find and call them. Call this at the bottom of a module after
    the class definition. Returns a list of method for __all__ variable,
    otherwise command 'fab -l' will show extra commands.
    """
    # get the module as an object
    module_obj = sys.modules[module_name]
    method_names_list = []

    # Iterate over the methods of the class and dynamically create a function
    # for each method that calls the method and add it to the current module
    for method in inspect.getmembers(instance, predicate=inspect.ismethod):
        method_name = method[0]

        if method_name.startswith('fab_'):
            func = getattr(instance, method_name)
            method_name = method_name.replace('fab_', '')
            setattr(module_obj, method_name, func)
            method_names_list += [method_name]

    return method_names_list


class BaseFabric:
    """
    Базовый класс для Fabric.
    """
    app_name = None
    git_branch = 'master'
    host = None
    project_folder_name = 'src'
    remote_base_path = '/var/venv/'
    repository = None
    user = 'deployer'

    def __init__(self, **kwargs):
        env.host_string = self.host
        env.user = self.user

    def activate_remote_venv(self):
        """
        Активировать виртуальное окружение на удаленном сервере.
        """
        return prefix('cd %s && source %s/bin/activate' % (
            self.get_remote_project_path(), self.get_remote_venv_path()))

    def get_local_venv_path(self):
        """
        Путь к локальному виртуальному окружению.
        """
        return os.path.dirname(self.get_local_project_path())

    def get_remote_venv_path(self):
        """
        Путь к удалённому виртуальному окружению.
        """
        return '%s%s' % (self.remote_base_path, self.app_name)

    def get_local_project_path(self):
        """
        Путь к локальному каталогу с проектом.
        """
        fab_module = sys.modules[self.__class__.__module__]
        return os.path.dirname(os.path.abspath(fab_module.__file__))

    def get_remote_project_path(self):
        """
        Путь к удалённому каталогу с проектом.
        """
        return os.path.join(self.get_remote_venv_path(),
                            self.project_folder_name)

    def get_db_backup_filename(self):
        """
        Название для бэкапа БД.
        """
        return os.path.join(
            self.get_remote_backups_path(),
            '%s-%s.sql' % (self.app_name, time.strftime('%Y-%m-%d.%H-%M-%S'))
        )

    def get_remote_backups_path(self):
        """
        Путь к бэкапам удалённого проекта.
        """
        return '/var/backups/%s' % self.app_name

    def fab_clear_local_cache(self):
        """
        Очистить Python кэш.
        """
        pattern = r'^.*\(__pycache__\|\.py[co]\)$'
        local('find . -regex "%s" -delete' % pattern)

    def fab_clear_remote_cache(self):
        """
        Очистить Python кэш удалённого проекта.
        """
        pattern = r'^.*\(__pycache__\|\.py[co]\)$'
        sudo('find %s -regex "%s" -delete' % (
            self.get_remote_venv_path(), pattern))

    def fab_push(self):
        """
        Отправить изменения из локального репозитория в основной.
        """
        local('git push origin %s' % self.git_branch)


class LocalDjangoMixin:
    """
    Специфичные команды для локального проекта.
    """

    def fab_run_local_manage_command(self, cmd='help'):
        """
        Выполнить 'python manage.py <command>' на локальном проекте.
        """
        with lcd(self.get_local_project_path()):
            return local('python manage.py %s' % cmd)

    def fab_local_pip(self, env='dev'):
        """
        Выполнить 'pip install -r requirements/{arg}.txt' на локальном проекте.
        """
        local('pip install -r requirements/%s.txt' % env)


class RemoteDjangoMixin:
    """
    Специфичные команды для удалённого проекта.
    """
    remote_db_name = None

    def create_remote_project_and_clone_repository(self):
        """
        Создать удалённый проект и склонировать туда репозиторий.
        """
        project_path = self.get_remote_project_path()

        if not exists(project_path, use_sudo=True):
            sudo('mkdir -p %s' % project_path)
            sudo('chown -R www-data:www-data %s' % project_path)
            sudo('chmod -R g+w %s' % project_path)

        if not exists('%s/.git' % project_path, use_sudo=True):
            run('git clone %s %s' % (self.repository, project_path))

    def update_remote_repository(self):
        """
        Обновить код удалённого проекта.
        """
        with self.activate_remote_venv():
            sudo('chown -R www-data:adm .git/')
            sudo('chmod -R 770 .git/')
            run('git checkout --force %s' % self.git_branch)
            run('git pull origin %s' % self.git_branch)

    def fab_run_remote_manage_command(self, cmd='help'):
        """
        Выполнить 'python manage.py <command>' на удалённом проекте.
        """
        with self.activate_remote_venv():
            return run('python manage.py %s' % cmd)

    def fab_remote_pip(self):
        """
        Выполнить 'pip install -r requirements.txt' на удалённом проекте.
        """
        with self.activate_remote_venv():
            run('pip install -r requirements.txt')

    def fab_remote_dumpdb(self):
        """
        Сделать дамп БД удалённого проекта.
        """
        sudo('mkdir -p %s' % self.get_remote_backups_path())
        backup_name = self.get_db_backup_filename()
        sudo('sudo -u postgres pg_dump -c %s > %s' % (
            self.remote_db_name, backup_name))
        return backup_name

    def fab_reload_uwsgi(self):
        """
        Перезапуск uwsgi.
        """
        sudo('touch %s/reload.me' % self.get_remote_venv_path())

    def fab_ipnb(self):
        """
        Запускает IPython Notebook на удалённом проекте.
        """
        self.fab_run_remote_manage_command('shell_plus --notebook')


class DjangoFabric(LocalDjangoMixin, RemoteDjangoMixin, BaseFabric):
    """
    Дополнения для Django.
    """
    local_db_name = None
    skip_remote_dumpdb = False
    skip_tests = False
    use_bower = False
    use_yarn = False

    def create_local_settings(self):
        """
        Создать ссылку на файл c локальными настройками.
        """
        with self.activate_remote_venv():
            run('ln -fs ../../../local_settings.py %s/settings/local.py' %
                self.app_name)

    def fab_test(self, app=''):
        """
        Запустить тесты на локальной машине.
        """
        self.fab_run_local_manage_command('test %s --nologcapture' % app)

    def fab_sync_media(self):
        """
        Синхронизирует файлы в папках media с удалённого проекта на локальный.
        """
        media_path = os.path.join(self.get_remote_project_path(), 'media')
        local_path = self.get_local_project_path()
        local('rsync -avhe ssh --no-perms %s:%s %s' % (
            env.host_string, media_path, local_path))
        local('sudo chown -R www-data:www-data %s/media' % local_path)
        local('sudo chmod -R g+w %s/media' % local_path)

    def fab_sync_db(self):
        """
        Копирует базу данных с удалённого проекта на локальный.
        """
        remote_db = self.fab_remote_dumpdb()
        get(remote_db, '/tmp/to.sql')
        local('sudo -i -u postgres psql %s < /tmp/to.sql' % self.local_db_name)
        local('sudo rm /tmp/to.sql')
        self.fab_clear_local_cache()
        self.fab_run_local_manage_command('migrate')

    def fab_sync_all(self):
        """
        Выполняет sync_media и sync_db.
        """
        self.fab_sync_media()
        self.fab_syncdb()

    def fab_deploy(self):
        """
        Деплой локального проекта на удалённый сервер.
        """
        if not self.skip_tests:
            self.fab_test()

        self.create_remote_project_and_clone_repository()

        if not self.skip_remote_dumpdb:
            self.fab_remote_dumpdb()

        self.fab_push()
        self.update_remote_repository()
        self.fab_clear_remote_cache()
        self.fab_remote_pip()
        self.create_local_settings()

        if self.use_bower:
            self.fab_run_remote_manage_command('bower install')

        if self.use_yarn:
            self.fab_run_remote_manage_command('yarn install')

        self.fab_run_remote_manage_command('migrate')
        self.fab_run_remote_manage_command('collectstatic --noinput')
        self.fab_reload_uwsgi()
