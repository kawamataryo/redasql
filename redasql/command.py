import argparse
import os
import re
import sys
from textwrap import dedent
from os.path import expanduser
from typing import Optional

from prompt_toolkit import prompt
from prompt_toolkit.history import FileHistory

import redasql.utils as utils
from redasql.api_client import ApiClient
from redasql.dto import CommandArgs, DataSourceResponse
from redasql.exceptions import RedasqlException, InsufficientParametersError
from redasql.metacommand_executor import (
    ConnectCommandExecutor,
    meta_command_factory,
)
from redasql.result_formatter import table_formatter, pivoted_formatter
from redasql.__version__ import __VERSION__


class MainCommand:

    def __init__(
        self,
        endpoint: str,
        api_key: str,
        proxy: str,
        data_source_name: Optional[str],
    ):
        self.endpoint = endpoint if endpoint else os.environ.get('REDASQL_REDASH_ENDPOINT')
        self.api_key = api_key if api_key else os.environ.get('REDASQL_REDASH_APIKEY')
        if self.endpoint is None or self.api_key is None:
            raise InsufficientParametersError("""
            "endpoint" and "api key" are absolutely necessary. use args or environment
            """)

        self.proxy = proxy if proxy else os.environ.get('REDASQL_HTTP_PROXY')
        self.client = ApiClient(
            redash_url=self.endpoint,
            api_key=self.api_key,
            proxy=self.proxy
        )
        self.pivoted = False
        self.data_source: Optional[DataSourceResponse] = None
        if data_source_name:
            executor = ConnectCommandExecutor(self.client, None, False)
            meta_command_return_list = executor.exec(data_source_name=data_source_name)
            if meta_command_return_list:
                meta_command_return_list.apply(self)

        self.input_buffer = []

        self.history = FileHistory(f'{expanduser("~")}/.redasql.hist')

    def splash(self):
        print(dedent(f"""
        ____          _                 _
        |  _ \ ___  __| | __ _ ___  __ _| |
        | |_) / _ \/ _` |/ _` / __|/ _` | |
        |  _ <  __/ (_| | (_| \__ \ (_| | |
        |_| \_\___|\__,_|\__,_|___/\__, |_|
                                      |_|
            - redash query cli tool -

        SUCCESS CONNECT
        - server version {self.get_version()}
        - client version {__VERSION__}
        """))

    def get_version(self):
        return self.client.get_version()

    def get_queries(self):
        return self.client.get_queries()

    def _execute_query(self, query: str, data_source_id: int):
        return self.client.execute_query(
            query=query,
            data_source_id=data_source_id,
            max_age=0,
        )

    def loop(self):
        while True:
            try:
                self.main()
            except RedasqlException as e:
                print(e)
            except KeyboardInterrupt:
                print('Cancel')
                self.input_buffer = []
            except EOFError:
                print('Sayonara!')
                sys.exit(0)

    def main(self):
        answer = prompt(self._get_prompt(), history=self.history)

        # ignore empty line. if no buffer.
        if not self.input_buffer and utils.is_empty(answer):
            return
        self.input_buffer.append(answer)
        if utils.is_meta_command(answer):
            self.execute_meta_command_handler(answer)
            self.input_buffer = []
            return

        if utils.is_sql_end(answer):
            self.execute_query_handler()
            self.input_buffer = []
            return

    def execute_query_handler(self):
        query = '\n'.join(self.input_buffer)
        query_result = self._execute_query(
            query=query,
            data_source_id=self.data_source.id
        )
        if query_result.rows_count == 0:
            print(dedent(f"""
            no rows returned.
            {query_result.runtime_for_display}
            """))
            return
        formatted_string = self._get_formatter()(query_result)
        print(formatted_string)
        print(dedent(f"""
        {query_result.rows_count_for_display}
        {query_result.runtime_for_display}
        """))

    def execute_meta_command_handler(self, input_string):
        command, *args = re.split(r'\s+', input_string.strip())
        executor = meta_command_factory(command)
        e = executor(self.client, self.data_source, self.pivoted)
        meta_command_return_list = e.exec(*args)
        if meta_command_return_list:
            meta_command_return_list.apply(self)

    def _get_prompt(self):
        data_source_name = '(No DataSource)'
        if self.data_source:
            data_source_name = f'{self.data_source.name}'
        suffix = '-' if self.input_buffer else '='
        return f'{data_source_name}{suffix}# '

    def _get_formatter(self):
        if self.pivoted:
            return pivoted_formatter
        return table_formatter


def main():
    args = init()
    try:
        command = MainCommand(**args.to_dict())
        command.splash()
    except Exception as e:
        print(f'[ERROR] {e}\n')
        sys.exit(1)

    command.loop()


def init():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        '-k',
        '--api-key',
        help='redash api key',
        default=None,
    )
    parser.add_argument(
        '-s',
        '--server-host',
        help='redash host i.e) https://your-redash-server/',
        default=None,
    )
    parser.add_argument(
        '-d',
        '--data-source',
        help=dedent("""
        initial datasource name.
        if not set, no datasource selected.
        """),
        default=None
    )
    parser.add_argument(
        '-p',
        '--proxy',
        help=dedent("""
        if you need proxy connection, set them
        i.e) http://user:pass@proxy-host:proxy-port'
        """),
        default=None,
    )
    args = parser.parse_args()
    return CommandArgs(
        api_key=args.api_key,
        endpoint=args.server_host,
        data_source_name=args.data_source,
        proxy=args.proxy,
    )


if __name__ == '__main__':
    main()
