package app.vibecode.mobile;

import android.graphics.Color;
import android.os.Bundle;

import androidx.core.view.WindowCompat;

import com.getcapacitor.BridgeActivity;

public class MainActivity extends BridgeActivity {
	@Override
	public void onCreate(Bundle savedInstanceState) {
		super.onCreate(savedInstanceState);

		WindowCompat.setDecorFitsSystemWindows(getWindow(), true);
		getWindow().setStatusBarColor(Color.parseColor("#050505"));
		getWindow().setNavigationBarColor(Color.parseColor("#050505"));
	}
}
