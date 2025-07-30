"""
Machine Learning Module for Cryptocurrency Trading
Enhances signal quality and predicts trade outcomes using ML algorithms
"""
import os
import logging
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import pickle
import joblib
from sklearn.ensemble import RandomForestClassifier, GradientBoostingClassifier
from sklearn.preprocessing import StandardScaler
from sklearn.model_selection import train_test_split
from sklearn.metrics import classification_report, confusion_matrix, accuracy_score
import matplotlib.pyplot as plt
import seaborn as sns

logger = logging.getLogger(__name__)

class MLPredictor:
    """Machine learning predictor for cryptocurrency trading signals"""
    
    def __init__(self, model_dir='ml_models'):
        """Initialize the ML predictor.
        
        Args:
            model_dir (str): Directory to save ML models
        """
        self.model_dir = model_dir
        os.makedirs(model_dir, exist_ok=True)
        
        # Initialize models
        self.models = {}
        self.scalers = {}
        
        logger.info(f"ML Predictor initialized with model directory: {model_dir}")
    
    def prepare_features(self, df):
        """Prepare features for ML model from OHLCV data.
        
        Args:
            df (DataFrame): OHLCV dataframe
            
        Returns:
            DataFrame: Feature dataframe
        """
        # Make a copy to avoid modifying original
        df = df.copy()
        
        # Basic price features
        df['returns'] = df['close'].pct_change()
        df['log_returns'] = np.log(df['close'] / df['close'].shift(1))
        
        # Volume features
        df['volume_change'] = df['volume'].pct_change()
        df['volume_ma5'] = df['volume'].rolling(window=5).mean()
        df['volume_ma20'] = df['volume'].rolling(window=20).mean()
        df['relative_volume'] = df['volume'] / df['volume_ma20']
        
        # Price momentum
        for window in [5, 10, 20]:
            df[f'momentum_{window}'] = df['close'] - df['close'].shift(window)
            df[f'momentum_pct_{window}'] = df['close'].pct_change(window)
        
        # Moving averages
        for window in [5, 10, 20, 50]:
            df[f'ma_{window}'] = df['close'].rolling(window=window).mean()
            df[f'ma_ratio_{window}'] = df['close'] / df[f'ma_{window}']
        
        # Bollinger Bands
        for window in [20]:
            df[f'bb_middle_{window}'] = df['close'].rolling(window=window).mean()
            df[f'bb_std_{window}'] = df['close'].rolling(window=window).std()
            df[f'bb_upper_{window}'] = df[f'bb_middle_{window}'] + 2 * df[f'bb_std_{window}']
            df[f'bb_lower_{window}'] = df[f'bb_middle_{window}'] - 2 * df[f'bb_std_{window}']
            df[f'bb_width_{window}'] = (df[f'bb_upper_{window}'] - df[f'bb_lower_{window}']) / df[f'bb_middle_{window}']
            df[f'bb_position_{window}'] = (df['close'] - df[f'bb_lower_{window}']) / (df[f'bb_upper_{window}'] - df[f'bb_lower_{window}'])
        
        # RSI
        delta = df['close'].diff()
        gain = delta.where(delta > 0, 0)
        loss = -delta.where(delta < 0, 0)
        
        avg_gain = gain.rolling(window=14).mean()
        avg_loss = loss.rolling(window=14).mean()
        
        rs = avg_gain / avg_loss
        df['rsi'] = 100 - (100 / (1 + rs))
        
        # MACD
        df['ema_12'] = df['close'].ewm(span=12, adjust=False).mean()
        df['ema_26'] = df['close'].ewm(span=26, adjust=False).mean()
        df['macd'] = df['ema_12'] - df['ema_26']
        df['macd_signal'] = df['macd'].ewm(span=9, adjust=False).mean()
        df['macd_hist'] = df['macd'] - df['macd_signal']
        
        # Volatility
        df['volatility'] = df['log_returns'].rolling(window=20).std() * np.sqrt(20)
        df['high_low_range'] = (df['high'] - df['low']) / df['close']
        
        # Average True Range (ATR)
        tr1 = df['high'] - df['low']
        tr2 = (df['high'] - df['close'].shift()).abs()
        tr3 = (df['low'] - df['close'].shift()).abs()
        df['tr'] = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
        df['atr_14'] = df['tr'].rolling(window=14).mean()
        df['atr_percent'] = df['atr_14'] / df['close'] * 100
        
        # Drop rows with NaN values
        df = df.dropna()
        
        return df
    
    def add_target_variable(self, df, forward_periods=10, threshold_pct=1.0):
        """Add target variable for supervised learning.
        
        Args:
            df (DataFrame): Feature dataframe
            forward_periods (int): Number of periods to look forward
            threshold_pct (float): Price movement threshold to consider positive
            
        Returns:
            DataFrame: Dataframe with target variable
        """
        df = df.copy()
        
        # Calculate future price change
        df['future_price'] = df['close'].shift(-forward_periods)
        df['future_return'] = (df['future_price'] - df['close']) / df['close'] * 100
        
        # Create binary classification target
        df['target'] = 0
        df.loc[df['future_return'] > threshold_pct, 'target'] = 1
        
        # Drop rows with NaN in target
        df = df.dropna()
        
        return df
    
    def train_model(self, df, symbol, timeframe, model_type='random_forest'):
        """Train ML model on historical data.
        
        Args:
            df (DataFrame): OHLCV dataframe
            symbol (str): Symbol name
            timeframe (str): Timeframe
            model_type (str): Model type ('random_forest' or 'gradient_boosting')
            
        Returns:
            dict: Training results
        """
        # Prepare features and target
        features_df = self.prepare_features(df)
        features_df = self.add_target_variable(features_df)
        
        if len(features_df) < 100:
            logger.warning(f"Insufficient data for {symbol} {timeframe}: {len(features_df)} rows")
            return None
        
        # Define features and target
        feature_columns = [
            'returns', 'log_returns', 'volume_change', 'relative_volume',
            'momentum_5', 'momentum_pct_10', 'momentum_pct_20',
            'ma_ratio_5', 'ma_ratio_10', 'ma_ratio_20', 'ma_ratio_50',
            'bb_width_20', 'bb_position_20',
            'rsi', 'macd', 'macd_signal', 'macd_hist',
            'volatility', 'high_low_range', 'atr_percent'
        ]
        
        X = features_df[feature_columns]
        y = features_df['target']
        
        # Split data
        X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, shuffle=False)
        
        # Scale features
        scaler = StandardScaler()
        X_train_scaled = scaler.fit_transform(X_train)
        X_test_scaled = scaler.transform(X_test)
        
        # Train model
        if model_type == 'random_forest':
            model = RandomForestClassifier(
                n_estimators=100, 
                max_depth=10, 
                random_state=42,
                class_weight='balanced'
            )
        else:  # gradient_boosting
            model = GradientBoostingClassifier(
                n_estimators=100,
                learning_rate=0.1,
                max_depth=5,
                random_state=42
            )
        
        model.fit(X_train_scaled, y_train)
        
        # Evaluate model
        y_pred = model.predict(X_test_scaled)
        y_prob = model.predict_proba(X_test_scaled)[:, 1]
        
        accuracy = accuracy_score(y_test, y_pred)
        report = classification_report(y_test, y_pred, output_dict=True)
        
        # Feature importance
        if model_type == 'random_forest':
            feature_importance = model.feature_importances_
        else:
            feature_importance = model.feature_importances_
        
        feature_imp_df = pd.DataFrame({
            'Feature': feature_columns,
            'Importance': feature_importance
        }).sort_values('Importance', ascending=False)
        
        # Save model and scaler
        model_id = f"{symbol.replace('/', '_')}_{timeframe}_{model_type}"
        model_path = os.path.join(self.model_dir, f"{model_id}_model.pkl")
        scaler_path = os.path.join(self.model_dir, f"{model_id}_scaler.pkl")
        
        joblib.dump(model, model_path)
        joblib.dump(scaler, scaler_path)
        
        # Store model and scaler in memory
        self.models[model_id] = model
        self.scalers[model_id] = scaler
        
        # Create confusion matrix visualization
        plt.figure(figsize=(8, 6))
        cm = confusion_matrix(y_test, y_pred)
        sns.heatmap(cm, annot=True, fmt='d', cmap='Blues')
        plt.title(f'Confusion Matrix - {symbol} {timeframe}')
        plt.xlabel('Predicted')
        plt.ylabel('Actual')
        plt.savefig(os.path.join(self.model_dir, f"{model_id}_confusion.png"))
        plt.close()
        
        # Create feature importance visualization
        plt.figure(figsize=(12, 8))
        sns.barplot(x='Importance', y='Feature', data=feature_imp_df.head(10))
        plt.title(f'Top 10 Feature Importance - {symbol} {timeframe}')
        plt.tight_layout()
        plt.savefig(os.path.join(self.model_dir, f"{model_id}_feature_importance.png"))
        plt.close()
        
        logger.info(f"Model trained for {symbol} {timeframe} with accuracy: {accuracy:.4f}")
        
        return {
            'model_id': model_id,
            'model_type': model_type,
            'accuracy': accuracy,
            'classification_report': report,
            'feature_importance': feature_imp_df.to_dict(),
            'model_path': model_path,
            'scaler_path': scaler_path
        }
    
    def load_model(self, model_id):
        """Load ML model from file.
        
        Args:
            model_id (str): Model ID
            
        Returns:
            tuple: (model, scaler)
        """
        if model_id in self.models and model_id in self.scalers:
            return self.models[model_id], self.scalers[model_id]
        
        model_path = os.path.join(self.model_dir, f"{model_id}_model.pkl")
        scaler_path = os.path.join(self.model_dir, f"{model_id}_scaler.pkl")
        
        if not os.path.exists(model_path) or not os.path.exists(scaler_path):
            logger.error(f"Model or scaler not found for {model_id}")
            return None, None
        
        try:
            model = joblib.load(model_path)
            scaler = joblib.load(scaler_path)
            
            # Cache in memory
            self.models[model_id] = model
            self.scalers[model_id] = scaler
            
            logger.info(f"Model loaded for {model_id}")
            return model, scaler
        except Exception as e:
            logger.error(f"Error loading model {model_id}: {str(e)}")
            return None, None
    
    def predict(self, df, symbol, timeframe, model_type='random_forest'):
        """Predict trade signal quality using ML model.
        
        Args:
            df (DataFrame): OHLCV dataframe
            symbol (str): Symbol name
            timeframe (str): Timeframe
            model_type (str): Model type
            
        Returns:
            dict: Prediction results
        """
        # Ensure we have enough data
        if len(df) < 50:
            logger.warning(f"Insufficient data for prediction: {len(df)} rows")
            return {'signal_quality': 0.5, 'prediction': 0, 'confidence': 0}
        
        # Prepare features
        features_df = self.prepare_features(df)
        
        # Get latest data point
        latest = features_df.iloc[-1:].copy()
        
        # Define feature columns
        feature_columns = [
            'returns', 'log_returns', 'volume_change', 'relative_volume',
            'momentum_5', 'momentum_pct_10', 'momentum_pct_20',
            'ma_ratio_5', 'ma_ratio_10', 'ma_ratio_20', 'ma_ratio_50',
            'bb_width_20', 'bb_position_20',
            'rsi', 'macd', 'macd_signal', 'macd_hist',
            'volatility', 'high_low_range', 'atr_percent'
        ]
        
        if not all(col in latest.columns for col in feature_columns):
            missing = [col for col in feature_columns if col not in latest.columns]
            logger.error(f"Missing features: {missing}")
            return {'signal_quality': 0.5, 'prediction': 0, 'confidence': 0}
        
        X = latest[feature_columns]
        
        # Load model
        model_id = f"{symbol.replace('/', '_')}_{timeframe}_{model_type}"
        model, scaler = self.load_model(model_id)
        
        if model is None or scaler is None:
            logger.warning(f"Model not found for {symbol} {timeframe}, using default prediction")
            return {'signal_quality': 0.5, 'prediction': 0, 'confidence': 0}
        
        # Scale features
        X_scaled = scaler.transform(X)
        
        # Make prediction
        prediction = model.predict(X_scaled)[0]
        confidence = model.predict_proba(X_scaled)[0, prediction]
        
        # Calculate signal quality (normalized probability)
        signal_quality = model.predict_proba(X_scaled)[0, 1]
        
        return {
            'signal_quality': signal_quality,
            'prediction': int(prediction),
            'confidence': confidence
        }
    
    def batch_train_models(self, data_dict, model_type='random_forest'):
        """Train models for multiple symbols and timeframes.
        
        Args:
            data_dict (dict): Dictionary with symbol->timeframe->dataframe
            model_type (str): Model type
            
        Returns:
            dict: Training results
        """
        results = {}
        for symbol, timeframes in data_dict.items():
            symbol_results = {}
            for timeframe, df in timeframes.items():
                logger.info(f"Training model for {symbol} {timeframe}")
                result = self.train_model(df, symbol, timeframe, model_type)
                symbol_results[timeframe] = result
            results[symbol] = symbol_results
        
        return results
    
    def evaluate_signals(self, df, signals, symbol, timeframe, model_type='random_forest'):
        """Evaluate trading signals using ML model.
        
        Args:
            df (DataFrame): OHLCV dataframe
            signals (list): List of signal dictionaries
            symbol (str): Symbol name
            timeframe (str): Timeframe
            model_type (str): Model type
            
        Returns:
            list: Enhanced signals with ML evaluation
        """
        # Load model
        model_id = f"{symbol.replace('/', '_')}_{timeframe}_{model_type}"
        model, scaler = self.load_model(model_id)
        
        if model is None or scaler is None:
            logger.warning(f"Model not found for {symbol} {timeframe}, skipping ML evaluation")
            return signals
        
        # Prepare features
        features_df = self.prepare_features(df)
        
        # Define feature columns
        feature_columns = [
            'returns', 'log_returns', 'volume_change', 'relative_volume',
            'momentum_5', 'momentum_pct_10', 'momentum_pct_20',
            'ma_ratio_5', 'ma_ratio_10', 'ma_ratio_20', 'ma_ratio_50',
            'bb_width_20', 'bb_position_20',
            'rsi', 'macd', 'macd_signal', 'macd_hist',
            'volatility', 'high_low_range', 'atr_percent'
        ]
        
        # Evaluate each signal
        enhanced_signals = []
        for signal in signals:
            # Get timestamp of signal
            signal_time = signal.get('timestamp')
            
            if signal_time is None:
                # If no timestamp, use the latest data
                X = features_df.iloc[-1:][feature_columns]
            else:
                # Find closest data point
                closest_idx = features_df.index[features_df['timestamp'].searchsorted(signal_time)]
                X = features_df.iloc[closest_idx:closest_idx+1][feature_columns]
            
            # Scale features
            X_scaled = scaler.transform(X)
            
            # Make prediction
            signal_quality = model.predict_proba(X_scaled)[0, 1]
            prediction = model.predict(X_scaled)[0]
            confidence = model.predict_proba(X_scaled)[0, prediction]
            
            # Enhance signal
            enhanced_signal = signal.copy()
            enhanced_signal['ml_quality'] = signal_quality
            enhanced_signal['ml_prediction'] = int(prediction)
            enhanced_signal['ml_confidence'] = confidence
            
            # Only include signal if ML agrees (prediction=1) or confidence is high enough
            if prediction == 1 or signal_quality >= 0.7:
                enhanced_signals.append(enhanced_signal)
        
        return enhanced_signals


if __name__ == "__main__":
    # Configure logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # Example usage
    import ccxt
    
    # Fetch some historical data
    exchange = ccxt.binance()
    symbol = 'BTC/USDT'
    timeframe = '1h'
    
    try:
        # Fetch last 500 candles
        ohlcv = exchange.fetch_ohlcv(symbol, timeframe, limit=500)
        df = pd.DataFrame(ohlcv, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
        df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
        
        # Create ML predictor
        ml_predictor = MLPredictor()
        
        # Train model
        result = ml_predictor.train_model(df, symbol, timeframe)
        print(f"Model trained with accuracy: {result['accuracy']:.4f}")
        
        # Make prediction
        prediction = ml_predictor.predict(df, symbol, timeframe)
        print(f"Signal quality: {prediction['signal_quality']:.4f}")
        print(f"Prediction: {prediction['prediction']} (Confidence: {prediction['confidence']:.4f})")
        
    except Exception as e:
        print(f"Error: {str(e)}")
