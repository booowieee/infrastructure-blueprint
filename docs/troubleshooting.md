# Решение проблем и устранение неполадок (Troubleshooting)

В данном документе собраны проблемы, с которыми я столкнулся в процессе настройки инфраструктуры, и способы их решения.

---

## 1. Проблемы с SSH-ключом в GitLab CI/CD

### Описание
При подключении раннера GitLab к production-серверу возникала ошибка аутентификации:
```
Load key "/builds/booowieee/infrastructure-blueprint.tmp/SSH_PRIVATE_KEY": invalid format
Permission denied, please try again.
```

### Причина
При копировании содержимого приватного SSH-ключа из Windows в поле переменных GitLab CI/CD (Settings → CI/CD → Variables):
1. В конце строк незаметно добавлялся Windows-перенос строки `\r` (CRLF).
2. После последней строки `-----END OPENSSH PRIVATE KEY-----` отсутствовал обязательный символ переноса строки, из-за чего парсер OpenSSH внутри Docker-контейнера считал ключ поврежденным.

### Решение
1. Получить ключ в Linux-терминале с помощью `cat ~/.ssh/id_ed25519`.
2. Скопировать его в буфер обмена без лишних символов.
3. При создании переменной `SSH_PRIVATE_KEY` в GitLab вставить ключ и нажать клавишу **Enter** после завершающей строки `-----END OPENSSH PRIVATE KEY-----`, чтобы добавить перенос строки.
4. Выставить тип переменной как **File**.

---

## 2. Elasticsearch падает при старте (Exit Code 137 / Bootstrap checks failed)

### Описание
Контейнер Elasticsearch запускался, но сразу же останавливался. В логах контейнера (`docker logs elasticsearch`) отображалась ошибка:
```
bootstrap check failure [1] of [1]: max virtual memory areas vm.max_map_count [65530] is too low, increase to at least [262144]
```

### Причина
По умолчанию операционная система Ubuntu ограничивает количество областей виртуальной памяти для процессов значением 65530. Для работы Elasticsearch этого недостаточно, ему требуется минимум 262144.

### Решение
В плейбук настройки сервера [setup_server.yml](file:///D:/infrastructure-blueprint/ansible/playbooks/setup_server.yml) добавлена задача, увеличивающая лимит через модуль ядра `sysctl` с флагом сохранения изменений после перезагрузки:
```yaml
- name: Set vm.max_map_count for Elasticsearch
  sysctl:
    name: vm.max_map_count
    value: '262144'
    state: present
    reload: yes
```

---

## 3. Контейнеры приложения не видят базу данных (network not found)

### Описание
При попытке развернуть приложение через GitLab CI/CD на стадии деплоя падала ошибка:
```
Error response from daemon: network app-network declared as external, but could not be found
```

### Причина
Поскольку приложение и вспомогательная инфраструктура (база данных, логи, мониторинг) разделены на два разных Docker Compose стека, они общаются через общую внешнюю сеть `app-network`. Если эта сеть не создана до запуска Compose-файла приложения, Docker не может запустить контейнеры.

### Решение
Создание внешней сети `app-network` добавлено в Ansible-плейбук подготовки хоста [setup_server.yml](file:///D:/infrastructure-blueprint/ansible/playbooks/setup_server.yml) через модуль `docker_network`. Сеть создается один раз при первоначальной настройке сервера.
```yaml
- name: Create shared Docker network
  docker_network:
    name: app-network
    state: present
```
В файлах `docker-compose.app.yml` и `docker-compose.infra.yml` сеть объявлена как внешняя:
```yaml
networks:
  app-network:
    external: true
```
