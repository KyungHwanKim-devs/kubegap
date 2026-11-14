Output run.gif
Set Shell "bash"
Set FontSize 15
Set Width 1280
Set Height 760
Set Padding 18
Set TypingSpeed 35ms
Set Theme "GitHub Dark"
Hide
Type "source env.sh"
Enter
Show
Type "kubegap evaluate --context demo"
Enter
Sleep 4s
Type "kubegap show findings --context demo --severity high | head -24"
Enter
Sleep 6s
Type "clear"
Enter
Type "kubegap show finding resilience.no-backup.cluster --context demo | head -22"
Enter
Sleep 7s
