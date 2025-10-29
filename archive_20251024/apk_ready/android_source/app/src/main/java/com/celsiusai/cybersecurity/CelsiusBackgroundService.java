package com.celsiusai.cybersecurity;

import android.app.Service;
import android.content.Intent;
import android.os.IBinder;
import android.os.Handler;
import android.os.Looper;
import android.widget.Toast;
import java.net.HttpURLConnection;
import java.net.URL;
import java.io.IOException;

public class CelsiusBackgroundService extends Service {
    private Handler handler;
    private Runnable connectionChecker;
    private String serverUrl = "http://192.168.1.100:5000";
    
    @Override
    public void onCreate() {
        super.onCreate();
        handler = new Handler(Looper.getMainLooper());
        
        connectionChecker = new Runnable() {
            @Override
            public void run() {
                checkConnection();
                handler.postDelayed(this, 30000); // Check every 30 seconds
            }
        };
    }
    
    @Override
    public int onStartCommand(Intent intent, int flags, int startId) {
        handler.post(connectionChecker);
        return START_STICKY; // Restart if killed
    }
    
    @Override
    public IBinder onBind(Intent intent) {
        return null;
    }
    
    private void checkConnection() {
        new Thread(() -> {
            try {
                URL url = new URL(serverUrl + "/api/status");
                HttpURLConnection connection = (HttpURLConnection) url.openConnection();
                connection.setConnectTimeout(3000);
                connection.setReadTimeout(3000);
                connection.setRequestMethod("GET");
                
                int responseCode = connection.getResponseCode();
                
                handler.post(() -> {
                    if (responseCode != 200) {
                        // Connection lost - could notify user or attempt reconnection
                    }
                });
                
            } catch (IOException e) {
                // Server unreachable
            }
        }).start();
    }
    
    @Override
    public void onDestroy() {
        super.onDestroy();
        if (handler != null && connectionChecker != null) {
            handler.removeCallbacks(connectionChecker);
        }
    }
}