package dev.sentinel.field

import android.app.job.JobInfo
import android.app.job.JobParameters
import android.app.job.JobScheduler
import android.app.job.JobService
import android.content.ComponentName
import android.content.Context
import java.util.concurrent.Executors

class HistoryCleanup : JobService() {
    private val executor = Executors.newSingleThreadExecutor()
    override fun onStartJob(params: JobParameters): Boolean {
        executor.execute {
            var retry = false
            try { HistoryStore(applicationContext).use { it.cleanup() } } catch (_: Exception) { retry = true }
            jobFinished(params, retry)
        }
        return true
    }
    override fun onStopJob(params: JobParameters): Boolean = true
    override fun onDestroy() { executor.shutdown(); super.onDestroy() }
    companion object {
        fun schedule(context: Context) {
            context.getSystemService(JobScheduler::class.java).schedule(JobInfo.Builder(1101, ComponentName(context, HistoryCleanup::class.java)).setPeriodic(24 * 3600_000L).build())
        }
    }
}
