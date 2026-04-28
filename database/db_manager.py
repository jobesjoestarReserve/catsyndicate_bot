import asyncpg
import os
from dotenv import load_dotenv

load_dotenv()

class DBManager:
    def __init__(self):
        self.url = os.getenv("DATABASE_URL")
        self.pool = None

    async def connect(self):
        if not self.pool:
            # Важно: используем create_pool для работы с acquire()
            self.pool = await asyncpg.create_pool(self.url)
            await self.ensure_schema()
            print("Пул подключений к БД создан")

    async def ensure_schema(self):
        async with self.pool.acquire() as conn:
            await conn.execute(
                "ALTER TABLE users ADD COLUMN IF NOT EXISTS last_seen timestamp without time zone"
            )
            await conn.execute("ALTER TABLE users ALTER COLUMN last_seen DROP DEFAULT")
            await conn.execute(
                "ALTER TABLE users ADD COLUMN IF NOT EXISTS authority integer DEFAULT 0"
            )
            await conn.execute("UPDATE users SET authority = 0 WHERE authority IS NULL")
            await conn.execute(
                "ALTER TABLE users ADD COLUMN IF NOT EXISTS life_xp integer DEFAULT 0"
            )
            await conn.execute("UPDATE users SET life_xp = 0 WHERE life_xp IS NULL")
            await conn.execute(
                """
                CREATE TABLE IF NOT EXISTS chat_activity (
                    chat_id bigint PRIMARY KEY,
                    last_seen timestamp without time zone NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    next_event_after timestamp without time zone NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    auto_events_enabled boolean NOT NULL DEFAULT true
                )
                """
            )
            await conn.execute(
                """
                CREATE TABLE IF NOT EXISTS chat_events (
                    id serial PRIMARY KEY,
                    chat_id bigint NOT NULL,
                    event_type text NOT NULL,
                    status text NOT NULL DEFAULT 'active',
                    hp_current integer NOT NULL DEFAULT 0,
                    hp_max integer NOT NULL DEFAULT 0,
                    reward_pool integer NOT NULL DEFAULT 0,
                    wool_pool integer NOT NULL DEFAULT 0,
                    metal_pool integer NOT NULL DEFAULT 0,
                    trash_pool integer NOT NULL DEFAULT 0,
                    created_at timestamp without time zone NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    ends_at timestamp without time zone NOT NULL
                )
                """
            )
            await conn.execute(
                """
                CREATE TABLE IF NOT EXISTS event_participants (
                    event_id integer NOT NULL REFERENCES chat_events(id) ON DELETE CASCADE,
                    user_id bigint NOT NULL REFERENCES users(user_id) ON DELETE CASCADE,
                    damage integer NOT NULL DEFAULT 0,
                    grabs integer NOT NULL DEFAULT 0,
                    last_action_at timestamp without time zone NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    PRIMARY KEY (event_id, user_id)
                )
                """
            )
            await conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_chat_events_active ON chat_events(chat_id, status, ends_at)"
            )
            await conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_chat_activity_spawn ON chat_activity(auto_events_enabled, last_seen, next_event_after)"
            )

    async def get_user(self, user_id):
        async with self.pool.acquire() as conn:
            return await conn.fetchrow("SELECT * FROM users WHERE user_id = $1", user_id)

    async def touch_user(self, user_id):
        async with self.pool.acquire() as conn:
            await conn.execute(
                "UPDATE users SET last_seen = CURRENT_TIMESTAMP WHERE user_id = $1",
                user_id
            )

    async def touch_chat(self, chat_id):
        async with self.pool.acquire() as conn:
            await conn.execute(
                """
                INSERT INTO chat_activity (chat_id, last_seen)
                VALUES ($1, CURRENT_TIMESTAMP)
                ON CONFLICT (chat_id)
                DO UPDATE SET last_seen = CURRENT_TIMESTAMP
                """,
                chat_id
            )

    async def is_user_recently_seen(self, user_id, seconds):
        async with self.pool.acquire() as conn:
            return await conn.fetchval(
                """
                SELECT last_seen IS NOT NULL
                   AND last_seen >= CURRENT_TIMESTAMP - ($2 * INTERVAL '1 second')
                FROM users
                WHERE user_id = $1
                """,
                user_id,
                seconds,
            )

    async def update_balance(self, user_id, amount):
        async with self.pool.acquire() as conn:
            return await conn.fetchval(
                "UPDATE users SET balance = GREATEST(COALESCE(balance, 0) + $1, 0) WHERE user_id = $2 RETURNING balance",
                amount, user_id
            )

    async def set_balance(self, user_id, amount):
        async with self.pool.acquire() as conn:
            return await conn.fetchval(
                "UPDATE users SET balance = GREATEST($1, 0) WHERE user_id = $2 RETURNING balance",
                amount, user_id
            )

    async def update_mice_count(self, user_id, amount):
        async with self.pool.acquire() as conn:
            await conn.execute(
                "UPDATE users SET mice_count = GREATEST(COALESCE(mice_count, 0) + $1, 0) WHERE user_id = $2",
                amount, user_id
            )

    async def spend_mice(self, user_id, amount):
        async with self.pool.acquire() as conn:
            return await conn.fetchval(
                """
                UPDATE users
                SET mice_count = mice_count - $1
                WHERE user_id = $2 AND COALESCE(mice_count, 0) >= $1
                RETURNING mice_count
                """,
                amount, user_id
            )

    async def complete_mouse_work(self, user_id, mice_spent, fish_reward, mice_returned):
        async with self.pool.acquire() as conn:
            async with conn.transaction():
                updated = await conn.fetchrow(
                    """
                    UPDATE users
                    SET
                        mice_count = COALESCE(mice_count, 0) - $1 + $2,
                        balance = GREATEST(COALESCE(balance, 0) + $3, 0)
                    WHERE user_id = $4 AND COALESCE(mice_count, 0) >= $1
                    RETURNING balance, mice_count
                    """,
                    mice_spent, mice_returned, fish_reward, user_id
                )
                return updated

    async def add_inventory_item(self, user_id, item_name, item_type, amount):
        async with self.pool.acquire() as conn:
            async with conn.transaction():
                row = await conn.fetchrow(
                    """
                    SELECT id, bonus_value
                    FROM inventory
                    WHERE user_id = $1 AND item_name = $2 AND item_type = $3 AND is_equipped = false
                    ORDER BY id
                    LIMIT 1
                    FOR UPDATE
                    """,
                    user_id, item_name, item_type
                )
                if row:
                    return await conn.fetchval(
                        "UPDATE inventory SET bonus_value = COALESCE(bonus_value, 0) + $1 WHERE id = $2 RETURNING bonus_value",
                        amount, row["id"]
                    )
                return await conn.fetchval(
                    """
                    INSERT INTO inventory (user_id, item_name, item_type, bonus_value, is_equipped)
                    VALUES ($1, $2, $3, $4, false)
                    RETURNING bonus_value
                    """,
                    user_id, item_name, item_type, amount
                )

    async def add_resources(self, user_id, resources):
        async with self.pool.acquire() as conn:
            async with conn.transaction():
                totals = {}
                for item_name, amount in resources.items():
                    row = await conn.fetchrow(
                        """
                        SELECT id, bonus_value
                        FROM inventory
                        WHERE user_id = $1 AND item_name = $2 AND item_type = 'resource' AND is_equipped = false
                        ORDER BY id
                        LIMIT 1
                        FOR UPDATE
                        """,
                        user_id, item_name
                    )
                    if row:
                        total = await conn.fetchval(
                            "UPDATE inventory SET bonus_value = COALESCE(bonus_value, 0) + $1 WHERE id = $2 RETURNING bonus_value",
                            amount, row["id"]
                        )
                    else:
                        total = await conn.fetchval(
                            """
                            INSERT INTO inventory (user_id, item_name, item_type, bonus_value, is_equipped)
                            VALUES ($1, $2, 'resource', $3, false)
                            RETURNING bonus_value
                            """,
                            user_id, item_name, amount
                        )
                    totals[item_name] = total
                return totals

    async def complete_mice_mining(self, user_id, mice_spent, mice_returned, resources):
        async with self.pool.acquire() as conn:
            async with conn.transaction():
                updated = await conn.fetchrow(
                    """
                    UPDATE users
                    SET mice_count = COALESCE(mice_count, 0) - $1 + $2
                    WHERE user_id = $3 AND COALESCE(mice_count, 0) >= $1
                    RETURNING mice_count
                    """,
                    mice_spent, mice_returned, user_id
                )
                if not updated:
                    return None

                totals = {}
                for item_name, amount in resources.items():
                    row = await conn.fetchrow(
                        """
                        SELECT id, bonus_value
                        FROM inventory
                        WHERE user_id = $1 AND item_name = $2 AND item_type = 'resource' AND is_equipped = false
                        ORDER BY id
                        LIMIT 1
                        FOR UPDATE
                        """,
                        user_id, item_name
                    )
                    if row:
                        total = await conn.fetchval(
                            "UPDATE inventory SET bonus_value = COALESCE(bonus_value, 0) + $1 WHERE id = $2 RETURNING bonus_value",
                            amount, row["id"]
                        )
                    else:
                        total = await conn.fetchval(
                            """
                            INSERT INTO inventory (user_id, item_name, item_type, bonus_value, is_equipped)
                            VALUES ($1, $2, 'resource', $3, false)
                            RETURNING bonus_value
                            """,
                            user_id, item_name, amount
                        )
                    totals[item_name] = total

                return {
                    "mice_count": updated["mice_count"],
                    "resources": totals,
                }

    async def get_resources(self, user_id):
        async with self.pool.acquire() as conn:
            return await conn.fetch(
                """
                SELECT item_name, COALESCE(SUM(bonus_value), 0) AS amount
                FROM inventory
                WHERE user_id = $1 AND item_type = 'resource'
                GROUP BY item_name
                ORDER BY item_name
                """,
                user_id
            )

    async def get_cooldown(self, user_id, command):
        async with self.pool.acquire() as conn:
            return await conn.fetchval(
                "SELECT available_at FROM cooldowns WHERE user_id = $1 AND command = $2",
                user_id, command
            )

    async def set_cooldown(self, user_id, command, available_at):
        async with self.pool.acquire() as conn:
            await conn.execute(
                """
                INSERT INTO cooldowns (user_id, command, available_at)
                VALUES ($1, $2, $3)
                ON CONFLICT (user_id, command)
                DO UPDATE SET available_at = EXCLUDED.available_at
                """,
                user_id, command, available_at
            )

    async def register_user(self, user_id, name):
        async with self.pool.acquire() as conn:
            await conn.execute(
                "INSERT INTO users (user_id, cat_name, life_stage, balance, last_seen, authority) VALUES ($1, $2, 1, 100, CURRENT_TIMESTAMP, 0)",
                user_id, name
            )

    async def update_cat_name(self, user_id, name):
        async with self.pool.acquire() as conn:
            return await conn.fetchval(
                "UPDATE users SET cat_name = $1 WHERE user_id = $2 RETURNING cat_name",
                name, user_id
            )

    async def update_authority(self, user_id, amount):
        async with self.pool.acquire() as conn:
            return await conn.fetchval(
                "UPDATE users SET authority = GREATEST(COALESCE(authority, 0) + $1, 0) WHERE user_id = $2 RETURNING authority",
                amount, user_id
            )

    async def apply_grow_result(self, user_id, fish_cost, new_life_stage, new_life_xp):
        async with self.pool.acquire() as conn:
            return await conn.fetchrow(
                """
                UPDATE users
                SET
                    balance = GREATEST(COALESCE(balance, 0) - $1, 0),
                    life_xp = $2,
                    life_stage = $3,
                    last_seen = CURRENT_TIMESTAMP
                WHERE user_id = $4 AND COALESCE(balance, 0) >= $1
                RETURNING balance, life_xp, life_stage, authority, mice_count
                """,
                fish_cost,
                new_life_xp,
                new_life_stage,
                user_id,
            )

    async def apply_bite_result(
        self,
        attacker_id,
        target_id,
        attacker_mice_delta,
        attacker_fish_delta,
        attacker_authority_delta,
        target_mice_delta,
        target_fish_delta,
        target_authority_delta,
    ):
        async with self.pool.acquire() as conn:
            async with conn.transaction():
                attacker = await conn.fetchrow(
                    """
                    UPDATE users
                    SET
                        mice_count = GREATEST(COALESCE(mice_count, 0) + $1, 0),
                        balance = GREATEST(COALESCE(balance, 0) + $2, 0),
                        authority = GREATEST(COALESCE(authority, 0) + $3, 0),
                        last_seen = CURRENT_TIMESTAMP
                    WHERE user_id = $4
                    RETURNING balance, mice_count, authority
                    """,
                    attacker_mice_delta,
                    attacker_fish_delta,
                    attacker_authority_delta,
                    attacker_id,
                )
                target = await conn.fetchrow(
                    """
                    UPDATE users
                    SET
                        mice_count = GREATEST(COALESCE(mice_count, 0) + $1, 0),
                        balance = GREATEST(COALESCE(balance, 0) + $2, 0),
                        authority = GREATEST(COALESCE(authority, 0) + $3, 0)
                    WHERE user_id = $4
                    RETURNING balance, mice_count, authority
                    """,
                    target_mice_delta,
                    target_fish_delta,
                    target_authority_delta,
                    target_id,
                )
                return {"attacker": attacker, "target": target}

    async def get_top_cats(self, limit=5):
        async with self.pool.acquire() as conn:
            # Убедись, что здесь нет двойного async
            return await conn.fetch("SELECT cat_name, balance, life_stage FROM users ORDER BY balance DESC LIMIT $1", limit)
    
    async def get_top_authority(self, limit=10):
        async with self.pool.acquire() as conn:
            return await conn.fetch(
                """
                SELECT cat_name, authority, life_stage
                FROM users
                ORDER BY authority DESC, life_stage DESC, balance DESC
                LIMIT $1
                """,
                limit
            )

    async def get_active_event(self, chat_id):
        async with self.pool.acquire() as conn:
            return await conn.fetchrow(
                """
                SELECT *
                FROM chat_events
                WHERE chat_id = $1 AND status = 'active' AND ends_at > CURRENT_TIMESTAMP
                ORDER BY created_at DESC
                LIMIT 1
                """,
                chat_id
            )

    async def get_expired_active_events(self, limit=20):
        async with self.pool.acquire() as conn:
            return await conn.fetch(
                """
                SELECT *
                FROM chat_events
                WHERE status = 'active' AND ends_at <= CURRENT_TIMESTAMP
                ORDER BY ends_at
                LIMIT $1
                """,
                limit
            )

    async def create_chat_event(
        self,
        chat_id,
        event_type,
        hp_max,
        reward_pool,
        wool_pool,
        metal_pool,
        trash_pool,
        ends_at,
    ):
        async with self.pool.acquire() as conn:
            async with conn.transaction():
                active = await conn.fetchrow(
                    """
                    SELECT id
                    FROM chat_events
                    WHERE chat_id = $1 AND status = 'active' AND ends_at > CURRENT_TIMESTAMP
                    LIMIT 1
                    FOR UPDATE
                    """,
                    chat_id
                )
                if active:
                    return None
                return await conn.fetchrow(
                    """
                    INSERT INTO chat_events (
                        chat_id, event_type, hp_current, hp_max, reward_pool,
                        wool_pool, metal_pool, trash_pool, ends_at
                    )
                    VALUES ($1, $2, $3, $3, $4, $5, $6, $7, $8)
                    RETURNING *
                    """,
                    chat_id,
                    event_type,
                    hp_max,
                    reward_pool,
                    wool_pool,
                    metal_pool,
                    trash_pool,
                    ends_at,
                )

    async def close_chat_event(self, event_id, status):
        async with self.pool.acquire() as conn:
            return await conn.fetchrow(
                """
                UPDATE chat_events
                SET status = $1
                WHERE id = $2 AND status = 'active'
                RETURNING *
                """,
                status,
                event_id,
            )

    async def list_active_events(self):
        async with self.pool.acquire() as conn:
            return await conn.fetch(
                """
                SELECT *
                FROM chat_events
                WHERE status = 'active' AND ends_at > CURRENT_TIMESTAMP
                ORDER BY ends_at
                """
            )

    async def set_chat_event_cooldown(self, chat_id, next_event_after):
        async with self.pool.acquire() as conn:
            await conn.execute(
                """
                INSERT INTO chat_activity (chat_id, next_event_after)
                VALUES ($1, $2)
                ON CONFLICT (chat_id)
                DO UPDATE SET next_event_after = EXCLUDED.next_event_after
                """,
                chat_id,
                next_event_after,
            )

    async def set_chat_auto_events(self, chat_id, enabled):
        async with self.pool.acquire() as conn:
            await conn.execute(
                """
                INSERT INTO chat_activity (chat_id, auto_events_enabled)
                VALUES ($1, $2)
                ON CONFLICT (chat_id)
                DO UPDATE SET auto_events_enabled = EXCLUDED.auto_events_enabled
                """,
                chat_id,
                enabled,
            )

    async def get_autospawn_candidate_chats(self, active_seconds, limit=20):
        async with self.pool.acquire() as conn:
            return await conn.fetch(
                """
                SELECT ca.chat_id
                FROM chat_activity ca
                WHERE ca.auto_events_enabled = true
                  AND ca.last_seen >= CURRENT_TIMESTAMP - ($1 * INTERVAL '1 second')
                  AND ca.next_event_after <= CURRENT_TIMESTAMP
                  AND NOT EXISTS (
                      SELECT 1
                      FROM chat_events ce
                      WHERE ce.chat_id = ca.chat_id
                        AND ce.status = 'active'
                        AND ce.ends_at > CURRENT_TIMESTAMP
                  )
                ORDER BY ca.last_seen DESC
                LIMIT $2
                """,
                active_seconds,
                limit,
            )

    async def add_boss_damage(self, event_id, user_id, damage):
        async with self.pool.acquire() as conn:
            async with conn.transaction():
                event = await conn.fetchrow(
                    """
                    UPDATE chat_events
                    SET hp_current = GREATEST(hp_current - $1, 0)
                    WHERE id = $2 AND status = 'active' AND event_type = 'boss' AND ends_at > CURRENT_TIMESTAMP
                    RETURNING *
                    """,
                    damage,
                    event_id,
                )
                if not event:
                    return None
                participant = await conn.fetchrow(
                    """
                    INSERT INTO event_participants (event_id, user_id, damage, last_action_at)
                    VALUES ($1, $2, $3, CURRENT_TIMESTAMP)
                    ON CONFLICT (event_id, user_id)
                    DO UPDATE SET
                        damage = event_participants.damage + EXCLUDED.damage,
                        last_action_at = CURRENT_TIMESTAMP
                    RETURNING *
                    """,
                    event_id,
                    user_id,
                    damage,
                )
                return {"event": event, "participant": participant}

    async def finish_boss_event(self, event_id, participant_reward, authority_reward):
        async with self.pool.acquire() as conn:
            async with conn.transaction():
                event = await conn.fetchrow(
                    """
                    UPDATE chat_events
                    SET status = 'completed'
                    WHERE id = $1 AND status = 'active' AND hp_current <= 0
                    RETURNING *
                    """,
                    event_id,
                )
                if not event:
                    return None
                participants = await conn.fetch(
                    "SELECT user_id, damage FROM event_participants WHERE event_id = $1",
                    event_id,
                )
                for row in participants:
                    await conn.execute(
                        """
                        UPDATE users
                        SET
                            balance = GREATEST(COALESCE(balance, 0) + $1, 0),
                            authority = GREATEST(COALESCE(authority, 0) + $2, 0)
                        WHERE user_id = $3
                        """,
                        participant_reward,
                        authority_reward,
                        row["user_id"],
                    )
                return {"event": event, "participants": participants}

    async def grab_event_loot(self, event_id, user_id, fish_amount, resources):
        async with self.pool.acquire() as conn:
            async with conn.transaction():
                event = await conn.fetchrow(
                    """
                    SELECT *
                    FROM chat_events
                    WHERE id = $1 AND status = 'active' AND event_type IN ('fish_drop', 'resource_drop') AND ends_at > CURRENT_TIMESTAMP
                    FOR UPDATE
                    """,
                    event_id,
                )
                if not event:
                    return None

                fish_taken = min(fish_amount, event["reward_pool"])
                wool_taken = min(resources.get("wool", 0), event["wool_pool"])
                metal_taken = min(resources.get("metal", 0), event["metal_pool"])
                trash_taken = min(resources.get("trash", 0), event["trash_pool"])
                if fish_taken <= 0 and wool_taken <= 0 and metal_taken <= 0 and trash_taken <= 0:
                    return {"event": event, "empty": True}

                updated = await conn.fetchrow(
                    """
                    UPDATE chat_events
                    SET
                        reward_pool = reward_pool - $1,
                        wool_pool = wool_pool - $2,
                        metal_pool = metal_pool - $3,
                        trash_pool = trash_pool - $4
                    WHERE id = $5
                    RETURNING *
                    """,
                    fish_taken,
                    wool_taken,
                    metal_taken,
                    trash_taken,
                    event_id,
                )
                await conn.execute(
                    """
                    INSERT INTO event_participants (event_id, user_id, grabs, last_action_at)
                    VALUES ($1, $2, 1, CURRENT_TIMESTAMP)
                    ON CONFLICT (event_id, user_id)
                    DO UPDATE SET
                        grabs = event_participants.grabs + 1,
                        last_action_at = CURRENT_TIMESTAMP
                    """,
                    event_id,
                    user_id,
                )
                if fish_taken:
                    await conn.execute(
                        "UPDATE users SET balance = GREATEST(COALESCE(balance, 0) + $1, 0) WHERE user_id = $2",
                        fish_taken,
                        user_id,
                    )
                resource_taken = {
                    "wool": wool_taken,
                    "metal": metal_taken,
                    "trash": trash_taken,
                }
                for item_name, amount in resource_taken.items():
                    if amount <= 0:
                        continue
                    row = await conn.fetchrow(
                        """
                        SELECT id
                        FROM inventory
                        WHERE user_id = $1 AND item_name = $2 AND item_type = 'resource' AND is_equipped = false
                        ORDER BY id
                        LIMIT 1
                        FOR UPDATE
                        """,
                        user_id,
                        item_name,
                    )
                    if row:
                        await conn.execute(
                            "UPDATE inventory SET bonus_value = COALESCE(bonus_value, 0) + $1 WHERE id = $2",
                            amount,
                            row["id"],
                        )
                    else:
                        await conn.execute(
                            """
                            INSERT INTO inventory (user_id, item_name, item_type, bonus_value, is_equipped)
                            VALUES ($1, $2, 'resource', $3, false)
                            """,
                            user_id,
                            item_name,
                            amount,
                        )
                if (
                    updated["reward_pool"] <= 0
                    and updated["wool_pool"] <= 0
                    and updated["metal_pool"] <= 0
                    and updated["trash_pool"] <= 0
                ):
                    updated = await conn.fetchrow(
                        "UPDATE chat_events SET status = 'completed' WHERE id = $1 RETURNING *",
                        event_id,
                    )
                return {
                    "event": updated,
                    "fish": fish_taken,
                    "resources": {name: amount for name, amount in resource_taken.items() if amount > 0},
                    "empty": False,
                }

    async def delete_user(self, user_id):
        async with self.pool.acquire() as conn:
            async with conn.transaction():
                await conn.execute("DELETE FROM cooldowns WHERE user_id = $1", user_id)
                await conn.execute("DELETE FROM inventory WHERE user_id = $1", user_id)
                await conn.execute("DELETE FROM users WHERE user_id = $1", user_id)
            print(f"Пользователь {user_id} удален из базы.")

    async def close(self):
        if self.pool:
            await self.pool.close()
            print("Соединение с БД закрыто.")
        
db = DBManager()  # Готовый экземпляр для использования в других модулях
