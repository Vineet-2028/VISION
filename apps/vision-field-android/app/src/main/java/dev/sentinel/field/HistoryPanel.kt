package dev.sentinel.field

import androidx.compose.foundation.layout.*
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Modifier
import androidx.compose.ui.unit.dp
import org.json.JSONObject

@Composable fun HistoryPanel(entries: List<JSONObject>, enabled: Boolean, days: Int, onEnabled: (Boolean)->Unit, onDays: (Int)->Unit, onFeedback: (String,String)->Unit, onDelete: (String?)->Unit, onCache: ()->Unit, onExport: ()->Unit, onClose: ()->Unit) {
    var confirm by remember { mutableStateOf<String?>(null) }
    var sessions by remember { mutableStateOf(false) }
    AlertDialog(onDismissRequest=onClose, title={Text("Local history")}, confirmButton={TextButton(onClick=onClose){Text("Close")}}, text={
        Column {
            Text("Encrypted on this phone. No raw media, location trail or training contribution. Exports are separate copies.")
            Row { Text("Save new events", Modifier.weight(1f)); Switch(checked=enabled,onCheckedChange=onEnabled) }
            Text("Keep history: $days days · ${entries.size}/${HistoryPolicy.MAX_ROWS} records · 8 MiB database cap")
            Row { listOf(1,7,30,90).forEach { day -> TextButton(onClick={onDays(day)}) { Text("$day d") } } }
            Row { TextButton(onClick={sessions=false}){Text("Recent events")}; TextButton(onClick={sessions=true}){Text("Sessions")} }
            LazyColumn(Modifier.heightIn(max=260.dp)) {
                items(entries.filter { !sessions || it.optString("type")=="SESSION_SUMMARY" }, key={it.getString("event_id")}) { entry ->
                    Column(Modifier.fillMaxWidth().padding(vertical=10.dp)) {
                        Text(entry.getString("short_message"),style=MaterialTheme.typography.titleSmall)
                        Text(entry.getString("type")); Text(java.util.Date(entry.getLong("event_time_utc_ms")).toString())
                        Text(entry.optString("feedback", "Not rated"))
                        Row { listOf("USEFUL","NOT_USEFUL","UNSURE").forEach { value -> TextButton(enabled=enabled,onClick={onFeedback(entry.getString("event_id"),value)}) { Text(value.lowercase().replace('_',' ')) } } }
                        TextButton(onClick={confirm=entry.getString("event_id")}) { Text("Delete event") }
                        Text(entry.optJSONObject("details")?.toString(2) ?: "No further provenance", style=MaterialTheme.typography.bodySmall)
                    }
                }
            }
            Row { TextButton(onClick=onExport){Text("Export")}; TextButton(onClick=onCache){Text("Clear cache")} }
            TextButton(onClick={confirm="ALL"}) { Text("Delete all history") }
            Text("Turning history off stops new writes; it does not erase existing records. No remote copies are synchronized.")
        }
    })
    if (confirm!=null) AlertDialog(onDismissRequest={confirm=null}, title={Text("Delete local history?")}, text={Text("This removes the selected local records. Previously exported copies are not deleted. Private PC research benchmarks are unaffected.")}, confirmButton={TextButton(onClick={onDelete(if(confirm=="ALL") null else confirm); confirm=null}){Text("Delete")}}, dismissButton={TextButton(onClick={confirm=null}){Text("Cancel")}})
}
