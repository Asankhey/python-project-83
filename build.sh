#!/usr/bin/env bash
# скачиваем uv и запускаем установку зависимостей
curl -LsSf https://astral.sh/uv/install.sh | sh
source $HOME/.local/bin/env
make install
