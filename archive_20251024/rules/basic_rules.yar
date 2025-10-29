
            rule SuspiciousExecutable {
                meta:
                    description = "Detects potentially suspicious executables"
                    author = "Celsius AI"
                strings:
                    $s1 = "cmd.exe" nocase
                    $s2 = "powershell" nocase
                    $s3 = "mimikatz" nocase
                condition:
                    any of them
            }
            