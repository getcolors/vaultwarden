package main

import (
    "log"
    "net/http"
    "net/http/httputil"
    "net/url"
    "time"
)

func main() {
    upstream, _ := url.Parse("http://127.0.0.1:8080")
    proxy := httputil.NewSingleHostReverseProxy(upstream)
    client := &http.Client{Timeout: 3 * time.Second}
    mux := http.NewServeMux()
    mux.HandleFunc("/up", func(w http.ResponseWriter, _ *http.Request) {
        resp, err := client.Get(upstream.String() + "/alive")
        if err != nil || resp.StatusCode/100 != 2 {
            http.Error(w, "vaultwarden unavailable", http.StatusServiceUnavailable)
            return
        }
        resp.Body.Close()
        w.Header().Set("Content-Type", "text/plain")
        w.WriteHeader(http.StatusOK)
        _, _ = w.Write([]byte("ok\n"))
    })
    mux.Handle("/", proxy)
    server := &http.Server{Addr: ":80", Handler: mux, ReadHeaderTimeout: 10 * time.Second}
    log.Fatal(server.ListenAndServe())
}
