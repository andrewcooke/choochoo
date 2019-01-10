
BEGIN {
    RS = "\n\n"
    ORS = "\n\n"
}

/#\/bin\/bash/ {
    bash = "bash"
    print $0 |& bash
    close(bash, "to")
    while ((bash |& getline line) > 0)
        print line
    close(bash)
}

!/#\/bin\/bash/ {
    print $0
}
