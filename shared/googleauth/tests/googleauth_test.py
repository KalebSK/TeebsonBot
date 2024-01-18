from pytest_mock import MockerFixture
from sqlalchemy import text
import pytest
import googleauth
import json
import time
import asyncio

def reset_database(con):
    con.execute(text("DELETE FROM guild"))
    con.commit()
    con.close()

@pytest.mark.asyncio
async def test_get_auth_url(mocker):
    try:
        mocker.patch.object(googleauth, 'LINKED_FILE', 'linked_test.json')
        con = googleauth.get_connection()
        test_ga = googleauth.GoogeAuthConnect()
        auth_url = await test_ga.get_auth_url(guild_id='123')
        engine = googleauth.engine
        assert str(engine.url) == "sqlite:///:memory:"
        assert googleauth.LINKED_FILE == 'linked_test.json'

        # https://localhost:5000/authorize/123/random_string
        url_parts = auth_url.split('/')
        assert url_parts[4] == '123'
        assert isinstance(url_parts[5], str)
        assert len(test_ga.active_sign_ins) == 1

        guild = con.execute(
            text("SELECT * FROM guild WHERE guild_id = '123'")).fetchone()
        assert guild is not None
        guild = guild._asdict()
        assert guild['credential'] is None
        assert isinstance(guild['state'], str)
        await test_ga.stop_polling()

    finally:
        reset_database(con)

@pytest.mark.asyncio
async def test_get_credentials_valid(mocker: MockerFixture):
    try:
        mocker.patch.object(googleauth, 'LINKED_FILE', 'linked_test.json')
        con = googleauth.get_connection()
        test_ga = googleauth.GoogeAuthConnect()

        creds = json.dumps({
            "token": "abc",
            "refresh_token": "def",
            "token_uri": "https://accounts.google.com/o/oauth2/token",
            "client_id": "ghi",
            "client_secret": "jkl",
            "scopes": ['scope1', 'scope2', 'scope3'],
        })

        con.execute(text("INSERT INTO guild VALUES(:id, :credential, :state)"),
                    {
                        'id': '123',
                        'credential': creds,
                        'state': 'xyz'
                    })
        con.commit()

        creds, state = await test_ga.get_credentials(guild_id='123')
        assert state == 'xyz'
        assert creds['token'] == 'abc'
        assert creds['refresh_token'] == 'def'
        assert creds['token_uri'] == 'https://accounts.google.com/o/oauth2/token'
        assert creds['client_id'] == 'ghi'
        assert creds['client_secret'] == 'jkl'
        assert creds['scopes'] == ['scope1','scope2','scope3']

        await test_ga.stop_polling()
    finally:
        reset_database(con) 
@pytest.mark.asyncio
async def test_polling(mocker: MockerFixture):
    try:
        mocker.patch.object(googleauth, 'LINKED_FILE', 'linked_test.json')
        mocker.patch.object(googleauth, 'POLLING_INTERVAL', 0.1)
        con = googleauth.get_connection()
        test_ga = googleauth.GoogeAuthConnect()

        get_cred_spy = mocker.spy(test_ga, 'get_credentials')
        batch_spy = mocker.spy(test_ga, 'poll_batch')
        creds = json.dumps({
            "token": "abc",
            "refresh_token": "def",
            "token_uri": "https://accounts.google.com/o/oauth2/token",
            "client_id": "ghi",
            "client_secret": "jkl",
            "scopes": ['scope1', 'scope2', 'scope3'],
        })

        con.execute(text("INSERT INTO guild VALUES(:id, :credential, :state)"),
                    {
                        'id': '123',
                        'credential': creds,
                        'state': 'xyz'
                    })
        con.commit()

        test_ga.active_sign_ins = {'123': {'expire_time': time.time() + 300, 'state': 'xyz'}}

        assert len(test_ga.active_sign_ins) == 1

        # wait for the batch to process
        await asyncio.sleep(5)

        print(f'the batch spy: {batch_spy.await_count}')
        assert batch_spy.await_count == 1
        assert get_cred_spy.await_count == 1

        assert len(test_ga.linked) == 1
        assert test_ga.linked['123'] == json.loads(creds)
        assert len(test_ga.active_sign_ins) == 0

        await test_ga.stop_polling()

    finally:
        reset_database(con)
