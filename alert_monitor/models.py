class MonitorSession(models.Model):
    session_id = models.CharField(max_length=64, unique=True)
    started_at = models.DateTimeField(auto_now_add=True)
    last_activity = models.DateTimeField(auto_now=True)
    is_active = models.BooleanField(default=True)
    
    def __str__(self):
        return f"Session {self.session_id[:8]}... - {self.started_at}"

