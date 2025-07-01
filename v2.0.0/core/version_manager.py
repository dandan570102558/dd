class Version:
    def __init__(self, version_str: str = "V1.0.0"):
        if not version_str.startswith('V'):
            raise ValueError("Version must start with 'V'")
        self.prefix = 'V'
        self.major, self.minor, self.patch = map(int, version_str[1:].split('.'))
    
    def increment_major(self) -> str:
        """生成新版本号"""
        self.major += 1
        self.minor = 0
        self.patch = 0
        return str(self)
    
    def __str__(self) -> str:
        return f"{self.prefix}{self.major}.{self.minor}.{self.patch}"