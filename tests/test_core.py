import json
from pathlib import Path
import pytest
from core import Registry, atomic_write_env, parse_env, read_env_file, update_env, parse_routes, parse_schedule_list, group_route_segments, laravel_version, safe_artisan_args, project_valid, redacted, default_packages_for_major, laravel_php_compatible, latest_laravel_major


def test_env_preserves_comments_and_escaping():
    start = '# KEEP\nAPP_NAME="My App"\nDB_PASSWORD=secret\n\n# Ending\n'
    output = update_env(start, [('APP_NAME','Hello World'), ('DB_PASSWORD','new pass'),('APP_DEBUG','false')])
    assert output.startswith('# KEEP\nAPP_NAME="Hello World"')
    assert 'DB_PASSWORD="new pass"' in output
    assert '# Ending' in output
    assert dict((k, v) for k,v,_ in parse_env(output))['APP_NAME'] == 'Hello World'


def test_env_delete():
    assert 'OLD=' not in update_env('OLD=3\nNEW=4\n', [('NEW','4')])


def test_env_preserves_utf8_bom_crlf_and_unicode(tmp_path):
    path = tmp_path / '.env'
    path.write_bytes('\ufeff# Keep this comment\r\nAPP_NAME="Café App"\r\nDB_PASSWORD=old\r\n'.encode('utf-8'))
    original = read_env_file(path)
    assert original.startswith('\ufeff')
    assert '\r\n' in original and '\n' not in original.replace('\r\n', '')
    output = update_env(original, [('APP_NAME', '東京 App'), ('DB_PASSWORD', 'p@ss \\"word')])
    assert output.startswith('\ufeff# Keep this comment\r\n')
    assert '\n' not in output.replace('\r\n', '')
    path.write_bytes(output.encode('utf-8'))
    assert read_env_file(path) == output
    values = {key: value for key, value, _ in parse_env(output)}
    assert values['APP_NAME'] == '東京 App'
    assert values['DB_PASSWORD'] == 'p@ss \\"word'


def test_env_atomic_write_uses_unique_temp_and_keeps_original_on_failure(tmp_path, monkeypatch):
    path = tmp_path / '.env'
    path.write_text('APP_NAME=before\n', encoding='utf-8')
    collision = tmp_path / '.env.larevixo-tmp'
    collision.write_text('keep this unrelated file', encoding='utf-8')
    atomic_write_env(path, 'APP_NAME=after\n', path.stat().st_mode)
    assert path.read_text(encoding='utf-8') == 'APP_NAME=after\n'
    assert collision.read_text(encoding='utf-8') == 'keep this unrelated file'

    def fail_replace(source, destination):
        raise OSError('simulated replacement failure')

    monkeypatch.setattr('core.os.replace', fail_replace)
    with pytest.raises(OSError, match='simulated replacement failure'):
        atomic_write_env(path, 'APP_NAME=partial\n', path.stat().st_mode)
    assert path.read_text(encoding='utf-8') == 'APP_NAME=after\n'
    assert collision.read_text(encoding='utf-8') == 'keep this unrelated file'
    assert not list(tmp_path.glob('.env.larevixo-*.tmp'))


def test_routes():
    r = parse_routes(json.dumps([{'method':'GET|HEAD','uri':'api/users/{user}','name':'users.show','middleware':['api','auth:sanctum']}]))
    assert r[0]['uri']=='api/users/{user}'
    assert r[0]['middleware']=='api, auth:sanctum'


def test_routes_preserve_methods_and_group_nested_uri_segments():
    routes = parse_routes(json.dumps([
        {'method': 'GET|HEAD', 'uri': 'api/v1/users/{user}', 'middleware': ['api', 'auth']},
        {'method': 'POST', 'uri': 'api/v1/users/{user}', 'name': None, 'middleware': []},
    ]))
    assert len(routes) == 2
    assert [route['method'] for route in routes] == ['GET|HEAD', 'POST']
    assert routes[1]['name'] == ''
    assert group_route_segments(routes[0]['uri']) == ['api', 'v1', 'users']
    with pytest.raises(ValueError, match='JSON array'):
        parse_routes('{"routes": []}')


def test_route_parser_ignores_php_startup_warning_before_json():
    warning = 'Warning: Extension startup diagnostic\n'
    routes = parse_routes(warning + json.dumps([{'method': 'GET', 'uri': 'up'}]))
    assert routes[0]['uri'] == 'up'


def test_legacy_schedule_list_parser_handles_laravel_console_rows():
    output = '''
  */5  *        * * *  php artisan summarize:missing .......................................... Next Due: 2 دقیقه دیگر
  */10 *        * * *  php artisan projects:process-expired-reviews ........................... Next Due: 2 دقیقه دیگر
  0    8        * * *  php artisan projects:check-waiting-presenter ........................... Next Due: 19 ساعت دیگر
  *    *        * * *  php artisan projects:dispatch-admin2 .................................. Next Due: 17 ثانیه دیگر
  0    8        * * *  php artisan projects:check-no-suggestions --days=1 ..................... Next Due: 19 ساعت دیگر
  0    8        * * *  php artisan projects:check-no-suggestions --days=2 ..................... Next Due: 19 ساعت دیگر
  0    8        * * *  php artisan projects:check-no-suggestions --days=3 ..................... Next Due: 19 ساعت دیگر
  0    8        * * *  php artisan projects:check-no-suggestions --days=4 ..................... Next Due: 19 ساعت دیگر
  0    *        * * *  php artisan monitor:form-errors ....................................... Next Due: 12 دقیقه دیگر
  0    *        * * *  php artisan monitor:suspicious-orders ................................. Next Due: 12 دقیقه دیگر
  0    *        * * *  php artisan monitor:page-performance .................................. Next Due: 12 دقیقه دیگر
  0    9        * * *  php artisan reminders:todo-three-days .................................. Next Due: 20 ساعت دیگر
  0    10,13,16 * * *  php artisan reminders:todo-due-today .................................. Next Due: 12 دقیقه دیگر
  0    8        * * *  Closure at: app\\Console\\Kernel.php:67 .............................. Next Due: 19 ساعت دیگر
  *    *        * * *  php artisan magazine:sync ............................................. Next Due: 17 ثانیه دیگر
  *    *        * * *  check chat gpt available .............................................. Next Due: 17 ثانیه دیگر
  0    8        * * 6  Closure at: app\\Console\\Kernel.php:87 .............................. Next Due: 5 روز دیگر
  0    8        * * *  sends KPI reports every first jalali mounths ........................... Next Due: 19 ساعت دیگر
  0    8        * * *  Closure at: app\\Console\\Kernel.php:102 ............................. Next Due: 19 ساعت دیگر
  *    *        * * *  php artisan openai:update-fine-tune-status ............................ Next Due: 17 ثانیه دیگر
'''
    schedules = parse_schedule_list(output)
    assert len(schedules) == 20
    assert schedules[0]['expression'] == '*/5 * * * *'
    assert schedules[0]['test_name'] == 'summarize:missing'
    assert schedules[0]['next_due_date_human'] == '2 دقیقه دیگر'
    assert schedules[4]['test_name'] == 'projects:check-no-suggestions --days=1'
    assert schedules[13]['test_name'] is None
    assert schedules[15]['test_name'] == 'check chat gpt available'
    assert schedules[17]['test_name'] == 'sends KPI reports every first jalali mounths'
    assert schedules[18]['test_name'] is None


def test_safe_artisan():
    assert safe_artisan_args('make:controller', 'Admin/UserController', {'--api':True}) == ['make:controller','Admin/UserController','--api']
    with pytest.raises(ValueError):
        safe_artisan_args('make:model', 'Foo;rm -rf', {})


def test_redacted_masks_quoted_secrets_with_spaces():
    assert redacted('DB_PASSWORD="correct horse battery staple"') == 'DB_PASSWORD=[REDACTED]'
    assert redacted('AWS_SECRET_ACCESS_KEY: top secret value\nNext line') == 'AWS_SECRET_ACCESS_KEY: [REDACTED]\nNext line'


def test_laravel_creation_defaults_follow_selected_major_and_php():
    assert latest_laravel_major('8.3.1') == '13'
    assert latest_laravel_major('8.2.12') == '12'
    assert latest_laravel_major('8.1.26') == '10'
    assert not laravel_php_compatible('9.0.0', '13')
    with pytest.raises(ValueError, match='8.1'):
        latest_laravel_major('8.0.30')

    packages_10 = {package for package, _, _ in default_packages_for_major('10')}
    packages_12 = {package for package, _, _ in default_packages_for_major('12')}
    packages_13 = {package for package, _, _ in default_packages_for_major('13')}
    assert {'laravel/sanctum', 'laravel/sail', 'spatie/laravel-ignition'} <= packages_10
    assert {'laravel/pail', 'laravel/sail'} <= packages_12 and 'laravel/pao' not in packages_12
    assert {'laravel/pail', 'laravel/pao'} <= packages_13 and 'laravel/sail' not in packages_13


def test_registry_and_version(tmp_path):
    app=tmp_path/'proj'; app.mkdir(); (app/'artisan').write_text('')
    (app/'composer.json').write_text('{"require": {"laravel/framework": "^13.0"}}')
    (app/'composer.lock').write_text(json.dumps({'packages':[{'name':'laravel/framework','version':'v13.2.1'}]}))
    assert project_valid(app)
    assert laravel_version(app)=='13.2.1'
    store=Registry(tmp_path/'settings.json')
    store.add(app); store.add(app)
    assert len(store.projects)==1
    assert Registry(tmp_path/'settings.json').data['current']==str(app.resolve())


def test_registry_persists_unicode_and_space_paths(tmp_path):
    app = tmp_path / 'Projects ü' / 'Láravel App'
    app.mkdir(parents=True)
    (app / 'artisan').write_text('', encoding='utf-8')
    (app / 'composer.json').write_text('{"require":{"laravel/framework":"^12.0"}}', encoding='utf-8')
    filename = tmp_path / 'config' / 'settings.json'
    registry = Registry(filename)
    registry.add(app)
    reloaded = Registry(filename)
    assert reloaded.projects == [str(app.resolve())]
    assert reloaded.data['current'] == str(app.resolve())
