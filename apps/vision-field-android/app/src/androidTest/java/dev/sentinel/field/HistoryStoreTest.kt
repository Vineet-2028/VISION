package dev.sentinel.field

import androidx.test.platform.app.InstrumentationRegistry
import org.junit.Assert.*
import org.junit.Test

/** Requires a device. Never report these as executed from JVM-only verification. */
class HistoryStoreTest {
    @Test fun disabledHistoryExportAndDeletionPersistAcrossReopen() {
        val context = InstrumentationRegistry.getInstrumentation().targetContext
        val namespace = "history-test-" + java.util.UUID.randomUUID().toString().replace("-", "")
        HistoryStore(context, namespace).use { store ->
            store.deleteAll(); store.enabled=false
            store.record("CAPABILITY_CHANGED",null,"test")
            assertTrue(store.entries().isEmpty())
            store.export(); assertFalse(store.enabled)
            store.enabled=true; store.record("CAPABILITY_CHANGED",null,"Fixture unavailable")
            val id=store.entries().single().getString("event_id")
            store.feedback(id,"UNSURE")
            assertEquals("UNSURE",store.entries().single().getString("feedback"))
            store.delete(id)
        }
        HistoryStore(context, namespace).use { store -> assertTrue(store.entries().isEmpty()); store.enabled=false; store.deleteAll() }
        context.deleteDatabase("vision-$namespace.db")
        context.deleteSharedPreferences("vision-$namespace-policy")
    }

    @Test fun versionOneMigrationRetentionAndRowQuota() {
        val context = InstrumentationRegistry.getInstrumentation().targetContext
        val namespace = "history-test-" + java.util.UUID.randomUUID().toString().replace("-", "")
        val name = "vision-$namespace.db"
        context.openOrCreateDatabase(name, 0, null).use { db ->
            db.execSQL("CREATE TABLE records(id TEXT PRIMARY KEY, created INTEGER NOT NULL, expires INTEGER NOT NULL, payload BLOB NOT NULL)")
            db.version = 1
        }
        HistoryStore(context, namespace).use { store ->
            assertEquals(2, store.writableDatabase.version)
            store.enabled = true
            repeat(HistoryPolicy.MAX_ROWS + 1) { store.record("CAPABILITY_CHANGED", null, "fixture $it") }
            assertEquals(HistoryPolicy.MAX_ROWS, store.entries().size)
            store.days = 1
            store.readableDatabase.rawQuery("SELECT MAX(expires-created) FROM records", null).use {
                assertTrue(it.moveToFirst()); assertTrue(it.getLong(0) <= 86_400_000L)
            }
            store.writableDatabase.execSQL("UPDATE records SET expires=0")
            store.cleanup(); assertTrue(store.entries().isEmpty())
            store.deleteAll()
        }
        context.deleteDatabase(name)
        context.deleteSharedPreferences("vision-$namespace-policy")
    }
}
