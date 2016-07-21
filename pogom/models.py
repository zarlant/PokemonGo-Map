#!/usr/bin/python
# -*- coding: utf-8 -*-

import logging
from peewee import Model, SqliteDatabase, InsertQuery, IntegerField,\
                   CharField, FloatField, BooleanField, DateTimeField, PostgresqlDatabase

from datetime import datetime
from base64 import b64encode

from .utils import get_pokemon_name


db = SqliteDatabase('pogom.db')
# db = PostgresqlDatabase('postgres', host='localhost', port=5432, password='pokeDevPass1#', user='postgres')
log = logging.getLogger(__name__)


class BaseModel(Model):
    class Meta:
        database = db


class Pokemon(BaseModel):
    IGNORE = None
    ONLY = None

    # We are base64 encoding the ids delivered by the api
    # because they are too big for sqlite to handle
    encounter_id = CharField(primary_key=True)
    spawnpoint_id = CharField()
    pokemon_id = IntegerField()
    latitude = FloatField()
    longitude = FloatField()
    disappear_time = DateTimeField()
    detect_time = DateTimeField()

    @classmethod
    def get_active(cls, stamp): 
        r_stamp = datetime.fromtimestamp(int(stamp)/1e3)      
        query = (Pokemon
                 .select()
                 .where(Pokemon.disappear_time > datetime.utcnow())
                 .dicts())
        log.info("Get Pokemons for stamp: {}".format(r_stamp))
        pokemons = []
        for p in query:
            p['pokemon_name'] = get_pokemon_name(p['pokemon_id'])
            pokemon_name = p['pokemon_name'].lower()
            pokemon_id = str(p['pokemon_id'])
            if cls.IGNORE:
                if pokemon_name in cls.IGNORE or pokemon_id in cls.IGNORE:
                    continue
            if cls.ONLY:
                if pokemon_name not in cls.ONLY and pokemon_id not in cls.ONLY:
                    continue
            pokemons.append(p)

        return pokemons


class Pokestop(BaseModel):
    pokestop_id = CharField(primary_key=True)
    enabled = BooleanField()
    latitude = FloatField()
    longitude = FloatField()
    last_modified = DateTimeField()
    lure_expiration = DateTimeField(null=True)


class Gym(BaseModel):
    UNCONTESTED = 0
    TEAM_MYSTIC = 1
    TEAM_VALOR = 2
    TEAM_INSTINCT = 3

    gym_id = CharField(primary_key=True)
    team_id = IntegerField()
    guard_pokemon_id = IntegerField()
    gym_points = IntegerField()
    enabled = BooleanField()
    latitude = FloatField()
    longitude = FloatField()
    last_modified = DateTimeField()

class UserAccount(BaseModel):
    account_id = CharField(primary_key=True)
    location_string = CharField()


def parse_map(map_dict):
    pokemons = {}
    pokestops = {}
    gyms = {}

    detect_time = datetime.now()
    cells = map_dict['responses']['GET_MAP_OBJECTS']['map_cells']
    for cell in cells:
        for p in cell.get('wild_pokemons', []):
            pokemons[p['encounter_id']] = {
                'encounter_id': b64encode(str(p['encounter_id'])),
                'spawnpoint_id': p['spawnpoint_id'],
                'pokemon_id': p['pokemon_data']['pokemon_id'],
                'latitude': p['latitude'],
                'longitude': p['longitude'],
                'disappear_time': datetime.utcfromtimestamp(
                    (p['last_modified_timestamp_ms'] +
                     p['time_till_hidden_ms']) / 1000.0),
                'detect_time': detect_time
            }

        for f in cell.get('forts', []):
            if f.get('type') == 1:  # Pokestops
                if 'lure_info' in f:
                    lure_expiration = datetime.utcfromtimestamp(
                        f['lure_info']['lure_expires_timestamp_ms'] / 1000.0)
                else:
                    lure_expiration = None

                pokestops[f['id']] = {
                    'pokestop_id': f['id'],
                    'enabled': f['enabled'],
                    'latitude': f['latitude'],
                    'longitude': f['longitude'],
                    'last_modified': datetime.utcfromtimestamp(
                        f['last_modified_timestamp_ms'] / 1000.0),
                    'lure_expiration': lure_expiration
                }

            else:  # Currently, there are only stops and gyms
                gyms[f['id']] = {
                    'gym_id': f['id'],
                    'team_id': f['owned_by_team'],
                    'guard_pokemon_id': f['guard_pokemon_id'],
                    'gym_points': f['gym_points'],
                    'enabled': f['enabled'],
                    'latitude': f['latitude'],
                    'longitude': f['longitude'],
                    'last_modified': datetime.utcfromtimestamp(
                        f['last_modified_timestamp_ms'] / 1000.0),
                }

    if pokemons:
        log.info("Upserting {} pokemon".format(len(pokemons)))
        InsertQuery(Pokemon, rows=pokemons.values()).upsert().execute()

    if pokestops:
        log.info("Upserting {} pokestops".format(len(pokestops)))
        InsertQuery(Pokestop, rows=pokestops.values()).upsert().execute()

    if gyms:
        log.info("Upserting {} gyms".format(len(gyms)))
        InsertQuery(Gym, rows=gyms.values()).upsert().execute()


def create_tables():
    db.connect()
    db.create_tables([Pokemon, Pokestop, Gym], safe=True)
    db.close()
