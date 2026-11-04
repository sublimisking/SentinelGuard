class SecurityManager:
    def __init__(self,config):
        self.is_armed = False
        self.alarm_active = False

    def arm(self):
        self.is_armed = True
        print("SentinelGuard koruma modu aktif.")

    def disarm(self):
        self.is_armed = False
        print("SentinelGuard koruma modu devre disi.")
