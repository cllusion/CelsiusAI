package com.celsiusai.cybersecurity;

import android.app.Activity;
import android.os.Bundle;
import android.webkit.WebView;
import android.webkit.WebViewClient;
import android.webkit.WebSettings;
import android.content.Intent;
import android.net.Uri;
import android.widget.Toast;
import android.os.AsyncTask;
import java.net.HttpURLConnection;
import java.net.URL;
import java.io.IOException;

public class MainActivity extends Activity {
    private WebView webView;
    private String[] serverUrls = {
        "http://192.168.1.100:5000",  // Local network
        "https://your-ngrok-url.ngrok.io",  // Remote access (update with actual ngrok URL)
        "http://your-external-ip:5000"  // Direct external IP (update with your IP)
    };
    private String activeServerUrl;
    
    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);
        setContentView(R.layout.activity_main);
        
        webView = findViewById(R.id.webview);
        setupWebView();
        
        // Start background service
        Intent serviceIntent = new Intent(this, CelsiusBackgroundService.class);
        startService(serviceIntent);
        
        // Check server connection
        new ServerCheckTask().execute();
    }
    
    private void setupWebView() {
        WebSettings webSettings = webView.getSettings();
        webSettings.setJavaScriptEnabled(true);
        webSettings.setDomStorageEnabled(true);
        webSettings.setCacheMode(WebSettings.LOAD_DEFAULT);
        webSettings.setAllowContentAccess(true);
        webSettings.setAllowFileAccess(true);
        webSettings.setMixedContentMode(WebSettings.MIXED_CONTENT_ALWAYS_ALLOW);
        
        webView.setWebViewClient(new WebViewClient() {
            @Override
            public void onPageFinished(WebView view, String url) {
                super.onPageFinished(view, url);
                webView.evaluateJavascript(
                    "document.body.style.zoom='1.0';" +
                    "document.querySelector('meta[name=viewport]').setAttribute('content','width=device-width,initial-scale=1.0');",
                    null
                );
            }
            
            @Override
            public void onReceivedError(WebView view, int errorCode, String description, String failingUrl) {
                loadErrorPage();
            }
        });
    }
    
    private void loadCelsiusAI() {
        if (activeServerUrl != null) {
            webView.loadUrl(activeServerUrl);
        } else {
            loadErrorPage();
        }
    }
    
    private void loadErrorPage() {
        String errorHtml = "<html><body style='background:#1a1a2e;color:#fff;font-family:Arial;text-align:center;padding:50px;'>" +
            "<h1>Celsius AI</h1>" +
            "<h3>Connection Error</h3>" +
            "<p>Cannot connect to Celsius AI server</p>" +
            "<p>Please ensure your PC server is running:</p>" +
            "<p><code>" + serverUrl + "</code></p>" +
            "<button onclick='location.reload()' style='background:#00d4ff;color:#000;padding:10px 20px;border:none;border-radius:5px;margin:10px;'>Retry</button>" +
            "</body></html>";
        webView.loadDataWithBaseURL(null, errorHtml, "text/html", "UTF-8", null);
    }
    
    private class ServerCheckTask extends AsyncTask<Void, Void, String> {
        @Override
        protected String doInBackground(Void... params) {
            // Try each server URL until one works
            for (String url : serverUrls) {
                try {
                    URL serverUrl = new URL(url);
                    HttpURLConnection connection = (HttpURLConnection) serverUrl.openConnection();
                    connection.setConnectTimeout(3000);
                    connection.setReadTimeout(3000);
                    connection.setRequestMethod("GET");
                    
                    int responseCode = connection.getResponseCode();
                    if (responseCode == 200) {
                        return url;  // Return working URL
                    }
                } catch (IOException e) {
                    // Try next URL
                }
            }
            return null;  // No working server found
        }
        
        @Override
        protected void onPostExecute(String workingUrl) {
            if (workingUrl != null) {
                activeServerUrl = workingUrl;
                loadCelsiusAI();
                Toast.makeText(MainActivity.this, "Connected to Celsius AI", Toast.LENGTH_SHORT).show();
            } else {
                loadErrorPage();
                Toast.makeText(MainActivity.this, "Cannot reach any Celsius AI server", Toast.LENGTH_LONG).show();
            }
        }
    }
    
    @Override
    public void onBackPressed() {
        if (webView.canGoBack()) {
            webView.goBack();
        } else {
            super.onBackPressed();
        }
    }
}