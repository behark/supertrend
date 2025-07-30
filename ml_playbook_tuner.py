"""
ML-Based Self-Tuning Playbooks System
=====================================
Adaptive strategy evolution using trade performance and forecast accuracy.
Creates intelligent, self-improving trading strategies that learn from experience.
"""
import os
import json
import logging
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, asdict
import pickle
import joblib

# ML imports
from sklearn.ensemble import RandomForestRegressor, GradientBoostingRegressor
from sklearn.preprocessing import StandardScaler, LabelEncoder
from sklearn.model_selection import train_test_split, cross_val_score
from sklearn.metrics import mean_squared_error, r2_score, mean_absolute_error
from sklearn.cluster import KMeans

# Local imports
from trade_memory import TradeMemory, get_trade_memory
from playbook import Playbook
from ml_predictor import MLPredictor
from market_regime import MarketRegimeDetector

logger = logging.getLogger(__name__)

@dataclass
class PlaybookTuningRecommendation:
    """Recommendation for playbook parameter adjustments"""
    regime: str
    parameter: str
    current_value: float
    recommended_value: float
    confidence: float
    reasoning: str
    expected_improvement: float
    risk_level: str  # 'low', 'medium', 'high'

@dataclass
class TuningSession:
    """Complete tuning session results"""
    session_id: str
    timestamp: datetime
    recommendations: List[PlaybookTuningRecommendation]
    model_performance: Dict[str, float]
    data_quality_score: float
    total_trades_analyzed: int
    lookback_days: int

class MLPlaybookTuner:
    """
    ML-powered playbook optimization system that learns from trade history
    and forecast accuracy to continuously improve strategy parameters.
    """
    
    def __init__(self, data_dir: str = "data/ml_tuning"):
        """Initialize the ML playbook tuner.
        
        Args:
            data_dir (str): Directory for ML tuning data and models
        """
        self.data_dir = data_dir
        os.makedirs(data_dir, exist_ok=True)
        
        # Initialize components
        self.trade_memory = get_trade_memory()
        self.playbook = Playbook()
        self.ml_predictor = MLPredictor()
        self.regime_detector = MarketRegimeDetector()
        
        # ML models for different optimization tasks
        self.models = {
            'leverage_optimizer': None,
            'risk_ratio_optimizer': None,
            'confidence_threshold_optimizer': None,
            'strategy_weight_optimizer': None
        }
        
        # Feature scalers
        self.scalers = {}
        
        # Model paths
        self.model_paths = {
            name: os.path.join(data_dir, f"{name}.joblib") 
            for name in self.models.keys()
        }
        
        # Tuning history
        self.tuning_history_file = os.path.join(data_dir, "tuning_history.json")
        self.tuning_history = self._load_tuning_history()
        
        # Configuration
        self.config = {
            'min_trades_for_tuning': 50,
            'lookback_days': 30,
            'confidence_threshold': 0.7,
            'max_parameter_change': 0.3,  # Maximum 30% change per tuning
            'retraining_frequency': 7,  # Days between retraining
            'human_review_required': True
        }
        
        logger.info("ML Playbook Tuner initialized")
        
    def _load_tuning_history(self) -> List[Dict]:
        """Load tuning session history."""
        if os.path.exists(self.tuning_history_file):
            try:
                with open(self.tuning_history_file, 'r') as f:
                    return json.load(f)
            except Exception as e:
                logger.error(f"Error loading tuning history: {e}")
        return []
    
    def _save_tuning_history(self):
        """Save tuning session history."""
        try:
            with open(self.tuning_history_file, 'w') as f:
                json.dump(self.tuning_history, f, indent=2, default=str)
        except Exception as e:
            logger.error(f"Error saving tuning history: {e}")
    
    def prepare_training_data(self, lookback_days: int = 30) -> pd.DataFrame:
        """Prepare comprehensive training data from trade history.
        
        Args:
            lookback_days (int): Days of history to analyze
            
        Returns:
            DataFrame: Prepared training data with features and targets
        """
        # Get trade history
        trades = self.trade_memory.get_history(days=lookback_days, limit=1000)
        
        if len(trades) < self.config['min_trades_for_tuning']:
            raise ValueError(f"Insufficient trades for tuning. Need {self.config['min_trades_for_tuning']}, got {len(trades)}")
        
        # Convert to DataFrame
        trade_data = []
        for trade in trades:
            if trade.exit_price and trade.pnl is not None:
                trade_dict = asdict(trade)
                trade_data.append(trade_dict)
        
        df = pd.DataFrame(trade_data)
        
        # Feature engineering
        df = self._engineer_features(df)
        
        # Add performance targets
        df = self._add_performance_targets(df)
        
        logger.info(f"Prepared training data with {len(df)} trades and {len(df.columns)} features")
        return df
    
    def _engineer_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """Engineer features for ML training."""
        # Time-based features
        df['hour'] = pd.to_datetime(df['entry_time']).dt.hour
        df['day_of_week'] = pd.to_datetime(df['entry_time']).dt.dayofweek
        df['trade_duration_hours'] = (
            pd.to_datetime(df['exit_time']) - pd.to_datetime(df['entry_time'])
        ).dt.total_seconds() / 3600
        
        # Market condition features
        df['volatility_regime'] = df['regime'].map({
            'trending_up': 1, 'trending_down': -1, 'ranging': 0, 'volatile': 2
        })
        
        # Strategy performance features
        strategy_performance = df.groupby('strategy')['pnl'].agg(['mean', 'std', 'count'])
        df = df.merge(
            strategy_performance.add_suffix('_strategy_perf'), 
            left_on='strategy', right_index=True
        )
        
        # Symbol performance features
        symbol_performance = df.groupby('symbol')['pnl'].agg(['mean', 'std', 'count'])
        df = df.merge(
            symbol_performance.add_suffix('_symbol_perf'), 
            left_on='symbol', right_index=True
        )
        
        # Confidence-based features
        df['confidence_bin'] = pd.cut(df['confidence_score'], 
                                    bins=[0, 50, 70, 85, 100], 
                                    labels=['low', 'medium', 'high', 'very_high'])
        
        # Risk features
        df['actual_risk_ratio'] = np.where(
            df['pnl'] > 0, 
            df['pnl'] / abs(df['entry_price'] - df['stop_loss']),
            df['pnl'] / abs(df['entry_price'] - df['stop_loss'])
        )
        
        return df
    
    def _add_performance_targets(self, df: pd.DataFrame) -> pd.DataFrame:
        """Add target variables for optimization."""
        # Primary target: PnL efficiency (risk-adjusted returns)
        df['pnl_efficiency'] = df['pnl'] / df['quantity']  # Per unit return
        
        # Secondary targets
        df['win_rate'] = (df['pnl'] > 0).astype(int)
        df['risk_adjusted_return'] = df['pnl'] / df['quantity'] / df['leverage']
        df['drawdown_recovery'] = np.where(df['pnl'] < 0, abs(df['pnl']), 0)
        
        return df
    
    def train_optimization_models(self, df: pd.DataFrame) -> Dict[str, float]:
        """Train ML models for parameter optimization.
        
        Args:
            df (DataFrame): Prepared training data
            
        Returns:
            Dict: Model performance metrics
        """
        performance_metrics = {}
        
        # Prepare features
        feature_columns = [
            'leverage', 'confidence_score', 'volatility_regime', 'hour', 'day_of_week',
            'trade_duration_hours', 'pnl_strategy_perf_mean', 'pnl_symbol_perf_mean',
            'actual_risk_ratio'
        ]
        
        # Handle categorical variables
        df_encoded = df.copy()
        label_encoders = {}
        
        for col in ['strategy', 'symbol', 'confidence_bin']:
            if col in df_encoded.columns:
                le = LabelEncoder()
                df_encoded[f'{col}_encoded'] = le.fit_transform(df_encoded[col].astype(str))
                label_encoders[col] = le
                feature_columns.append(f'{col}_encoded')
        
        X = df_encoded[feature_columns].fillna(0)
        
        # Train leverage optimizer
        y_leverage = df_encoded['pnl_efficiency']
        self._train_single_model('leverage_optimizer', X, y_leverage, performance_metrics)
        
        # Train risk ratio optimizer  
        y_risk = df_encoded['risk_adjusted_return']
        self._train_single_model('risk_ratio_optimizer', X, y_risk, performance_metrics)
        
        # Train confidence threshold optimizer
        y_confidence = df_encoded['win_rate']
        self._train_single_model('confidence_threshold_optimizer', X, y_confidence, performance_metrics)
        
        logger.info(f"Trained {len(self.models)} optimization models")
        return performance_metrics
    
    def _train_single_model(self, model_name: str, X: pd.DataFrame, y: pd.Series, 
                          performance_metrics: Dict[str, float]):
        """Train a single optimization model."""
        try:
            # Split data
            X_train, X_test, y_train, y_test = train_test_split(
                X, y, test_size=0.2, random_state=42
            )
            
            # Scale features
            scaler = StandardScaler()
            X_train_scaled = scaler.fit_transform(X_train)
            X_test_scaled = scaler.transform(X_test)
            
            # Train model
            model = GradientBoostingRegressor(
                n_estimators=100,
                learning_rate=0.1,
                max_depth=6,
                random_state=42
            )
            
            model.fit(X_train_scaled, y_train)
            
            # Evaluate
            y_pred = model.predict(X_test_scaled)
            r2 = r2_score(y_test, y_pred)
            mae = mean_absolute_error(y_test, y_pred)
            
            # Store model and scaler
            self.models[model_name] = model
            self.scalers[model_name] = scaler
            
            # Save to disk
            joblib.dump({
                'model': model,
                'scaler': scaler,
                'feature_columns': list(X.columns)
            }, self.model_paths[model_name])
            
            performance_metrics[f'{model_name}_r2'] = r2
            performance_metrics[f'{model_name}_mae'] = mae
            
            logger.info(f"Trained {model_name}: R² = {r2:.3f}, MAE = {mae:.3f}")
            
        except Exception as e:
            logger.error(f"Error training {model_name}: {e}")
            performance_metrics[f'{model_name}_error'] = str(e)
    
    def generate_tuning_recommendations(self, lookback_days: int = 30) -> TuningSession:
        """Generate comprehensive playbook tuning recommendations.
        
        Args:
            lookback_days (int): Days of trade history to analyze
            
        Returns:
            TuningSession: Complete tuning recommendations
        """
        logger.info(f"Generating tuning recommendations for last {lookback_days} days")
        
        # Prepare and train on recent data
        df = self.prepare_training_data(lookback_days)
        model_performance = self.train_optimization_models(df)
        
        # Generate recommendations for each regime
        recommendations = []
        
        for regime in ['trending_up', 'trending_down', 'ranging', 'volatile']:
            regime_trades = df[df['regime'] == regime]
            
            if len(regime_trades) < 10:  # Need minimum trades per regime
                continue
                
            regime_recommendations = self._generate_regime_recommendations(
                regime, regime_trades, df
            )
            recommendations.extend(regime_recommendations)
        
        # Create tuning session
        session = TuningSession(
            session_id=f"tune_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
            timestamp=datetime.now(),
            recommendations=recommendations,
            model_performance=model_performance,
            data_quality_score=self._calculate_data_quality_score(df),
            total_trades_analyzed=len(df),
            lookback_days=lookback_days
        )
        
        # Save to history
        self.tuning_history.append(asdict(session))
        self._save_tuning_history()
        
        logger.info(f"Generated {len(recommendations)} tuning recommendations")
        return session
    
    def _generate_regime_recommendations(self, regime: str, regime_trades: pd.DataFrame, 
                                       full_df: pd.DataFrame) -> List[PlaybookTuningRecommendation]:
        """Generate recommendations for a specific market regime."""
        recommendations = []
        
        # Get current playbook settings
        current_playbook = self.playbook.get_playbook(regime)
        if not current_playbook:
            return recommendations
        
        # Analyze leverage optimization
        leverage_rec = self._optimize_leverage(regime, regime_trades, current_playbook)
        if leverage_rec:
            recommendations.append(leverage_rec)
        
        # Analyze risk ratio optimization
        risk_rec = self._optimize_risk_ratio(regime, regime_trades, current_playbook)
        if risk_rec:
            recommendations.append(risk_rec)
        
        # Analyze confidence threshold optimization
        conf_rec = self._optimize_confidence_threshold(regime, regime_trades, current_playbook)
        if conf_rec:
            recommendations.append(conf_rec)
        
        return recommendations
    
    def _optimize_leverage(self, regime: str, trades: pd.DataFrame, 
                         current_playbook: Dict) -> Optional[PlaybookTuningRecommendation]:
        """Optimize leverage for a specific regime."""
        if 'leverage_optimizer' not in self.models or self.models['leverage_optimizer'] is None:
            return None
        
        try:
            current_leverage = current_playbook.get('leverage', 1.0)
            
            # Calculate optimal leverage based on recent performance
            avg_pnl_efficiency = trades['pnl_efficiency'].mean()
            win_rate = (trades['pnl'] > 0).mean()
            volatility = trades['pnl'].std()
            
            # Conservative optimization: reduce leverage if high volatility, increase if consistent wins
            if win_rate > 0.6 and volatility < avg_pnl_efficiency * 0.5:
                recommended_leverage = min(current_leverage * 1.2, current_leverage + 0.5)
                reasoning = f"High win rate ({win_rate:.1%}) with low volatility suggests leverage increase"
                risk_level = "medium"
            elif win_rate < 0.4 or volatility > avg_pnl_efficiency:
                recommended_leverage = max(current_leverage * 0.8, current_leverage - 0.5)
                reasoning = f"Low win rate ({win_rate:.1%}) or high volatility suggests leverage reduction"
                risk_level = "low"
            else:
                return None  # No change needed
            
            # Apply maximum change limit
            max_change = current_leverage * self.config['max_parameter_change']
            recommended_leverage = np.clip(
                recommended_leverage, 
                current_leverage - max_change, 
                current_leverage + max_change
            )
            
            if abs(recommended_leverage - current_leverage) < 0.1:
                return None  # Change too small
            
            expected_improvement = abs(recommended_leverage - current_leverage) / current_leverage * avg_pnl_efficiency
            
            return PlaybookTuningRecommendation(
                regime=regime,
                parameter='leverage',
                current_value=current_leverage,
                recommended_value=recommended_leverage,
                confidence=min(win_rate + 0.3, 0.95),
                reasoning=reasoning,
                expected_improvement=expected_improvement,
                risk_level=risk_level
            )
            
        except Exception as e:
            logger.error(f"Error optimizing leverage for {regime}: {e}")
            return None
    
    def _optimize_risk_ratio(self, regime: str, trades: pd.DataFrame, 
                           current_playbook: Dict) -> Optional[PlaybookTuningRecommendation]:
        """Optimize risk/reward ratio for a specific regime."""
        try:
            current_ratio = current_playbook.get('risk_reward_ratio', 2.0)
            
            # Analyze actual risk/reward performance
            winning_trades = trades[trades['pnl'] > 0]
            losing_trades = trades[trades['pnl'] < 0]
            
            if len(winning_trades) == 0 or len(losing_trades) == 0:
                return None
            
            avg_win = winning_trades['pnl'].mean()
            avg_loss = abs(losing_trades['pnl'].mean())
            actual_ratio = avg_win / avg_loss if avg_loss > 0 else current_ratio
            
            # Recommend adjustment based on actual performance
            if actual_ratio > current_ratio * 1.3:
                recommended_ratio = min(current_ratio * 1.2, actual_ratio * 0.9)
                reasoning = f"Actual R:R ({actual_ratio:.1f}) exceeds target, can increase target"
                risk_level = "low"
            elif actual_ratio < current_ratio * 0.7:
                recommended_ratio = max(current_ratio * 0.8, actual_ratio * 1.1)
                reasoning = f"Actual R:R ({actual_ratio:.1f}) below target, should reduce target"
                risk_level = "medium"
            else:
                return None
            
            # Apply limits
            max_change = current_ratio * self.config['max_parameter_change']
            recommended_ratio = np.clip(
                recommended_ratio,
                current_ratio - max_change,
                current_ratio + max_change
            )
            
            if abs(recommended_ratio - current_ratio) < 0.2:
                return None
            
            expected_improvement = abs(recommended_ratio - current_ratio) / current_ratio * 0.1
            
            return PlaybookTuningRecommendation(
                regime=regime,
                parameter='risk_reward_ratio',
                current_value=current_ratio,
                recommended_value=recommended_ratio,
                confidence=0.8,
                reasoning=reasoning,
                expected_improvement=expected_improvement,
                risk_level=risk_level
            )
            
        except Exception as e:
            logger.error(f"Error optimizing risk ratio for {regime}: {e}")
            return None
    
    def _optimize_confidence_threshold(self, regime: str, trades: pd.DataFrame, 
                                     current_playbook: Dict) -> Optional[PlaybookTuningRecommendation]:
        """Optimize confidence threshold for trade execution."""
        try:
            current_threshold = current_playbook.get('min_confidence', 60.0)
            
            # Analyze performance by confidence levels
            confidence_bins = pd.cut(trades['confidence_score'], 
                                   bins=[0, 50, 65, 80, 100], 
                                   labels=['<50', '50-65', '65-80', '80+'])
            
            performance_by_confidence = trades.groupby(confidence_bins).agg({
                'pnl': ['mean', 'count'],
                'win_rate': 'mean'
            }).round(3)
            
            # Find optimal threshold
            best_threshold = current_threshold
            best_performance = -float('inf')
            
            for threshold in [50, 60, 70, 80]:
                high_conf_trades = trades[trades['confidence_score'] >= threshold]
                if len(high_conf_trades) < 5:
                    continue
                    
                avg_pnl = high_conf_trades['pnl'].mean()
                win_rate = (high_conf_trades['pnl'] > 0).mean()
                trade_count = len(high_conf_trades)
                
                # Score combines profitability, win rate, and trade frequency
                score = avg_pnl * win_rate * np.log(trade_count + 1)
                
                if score > best_performance:
                    best_performance = score
                    best_threshold = threshold
            
            if abs(best_threshold - current_threshold) < 5:
                return None
            
            reasoning = f"Optimal confidence threshold analysis suggests {best_threshold}%"
            expected_improvement = abs(best_threshold - current_threshold) / 100 * 0.05
            
            return PlaybookTuningRecommendation(
                regime=regime,
                parameter='min_confidence',
                current_value=current_threshold,
                recommended_value=best_threshold,
                confidence=0.75,
                reasoning=reasoning,
                expected_improvement=expected_improvement,
                risk_level="low"
            )
            
        except Exception as e:
            logger.error(f"Error optimizing confidence threshold for {regime}: {e}")
            return None
    
    def _calculate_data_quality_score(self, df: pd.DataFrame) -> float:
        """Calculate data quality score for the training dataset."""
        try:
            # Factors for data quality
            completeness = 1 - df.isnull().sum().sum() / (len(df) * len(df.columns))
            trade_count_score = min(len(df) / 100, 1.0)  # Prefer 100+ trades
            regime_diversity = len(df['regime'].unique()) / 4  # 4 main regimes
            time_coverage = min((df['entry_time'].max() - df['entry_time'].min()).days / 30, 1.0)
            
            score = (completeness * 0.3 + trade_count_score * 0.3 + 
                    regime_diversity * 0.2 + time_coverage * 0.2)
            
            return round(score, 3)
            
        except Exception as e:
            logger.error(f"Error calculating data quality score: {e}")
            return 0.5
    
    def apply_recommendations(self, session: TuningSession, 
                            auto_apply: bool = False) -> Dict[str, Any]:
        """Apply tuning recommendations to playbooks.
        
        Args:
            session (TuningSession): Tuning session with recommendations
            auto_apply (bool): Whether to apply automatically or require approval
            
        Returns:
            Dict: Application results
        """
        if not auto_apply and self.config['human_review_required']:
            logger.info("Human review required. Use approve_and_apply_recommendations()")
            return {'status': 'pending_review', 'recommendations': len(session.recommendations)}
        
        applied_count = 0
        errors = []
        
        for rec in session.recommendations:
            try:
                # Get current playbook
                current_playbook = self.playbook.get_playbook(rec.regime)
                if not current_playbook:
                    continue
                
                # Apply recommendation
                current_playbook[rec.parameter] = rec.recommended_value
                
                # Update playbook
                self.playbook.update_playbook(rec.regime, current_playbook)
                applied_count += 1
                
                logger.info(f"Applied {rec.parameter} = {rec.recommended_value} for {rec.regime}")
                
            except Exception as e:
                error_msg = f"Error applying {rec.parameter} for {rec.regime}: {e}"
                logger.error(error_msg)
                errors.append(error_msg)
        
        # Save updated playbooks
        self.playbook.save_playbooks()
        
        return {
            'status': 'completed',
            'applied_count': applied_count,
            'total_recommendations': len(session.recommendations),
            'errors': errors
        }
    
    def get_tuning_summary(self, days: int = 7) -> Dict[str, Any]:
        """Get summary of recent tuning activities."""
        recent_sessions = [
            session for session in self.tuning_history
            if datetime.fromisoformat(session['timestamp']) > datetime.now() - timedelta(days=days)
        ]
        
        if not recent_sessions:
            return {'message': 'No recent tuning sessions'}
        
        total_recommendations = sum(len(s['recommendations']) for s in recent_sessions)
        avg_data_quality = np.mean([s['data_quality_score'] for s in recent_sessions])
        
        return {
            'recent_sessions': len(recent_sessions),
            'total_recommendations': total_recommendations,
            'avg_data_quality_score': round(avg_data_quality, 3),
            'last_session': recent_sessions[-1]['timestamp'],
            'model_performance': recent_sessions[-1].get('model_performance', {})
        }


# Global instance
ml_tuner = None

def get_ml_tuner() -> MLPlaybookTuner:
    """Get global ML tuner instance."""
    global ml_tuner
    if ml_tuner is None:
        ml_tuner = MLPlaybookTuner()
    return ml_tuner

def initialize_ml_tuner(data_dir: str = "data/ml_tuning") -> MLPlaybookTuner:
    """Initialize global ML tuner instance."""
    global ml_tuner
    ml_tuner = MLPlaybookTuner(data_dir)
    return ml_tuner


if __name__ == "__main__":
    # Test the ML playbook tuner
    logging.basicConfig(level=logging.INFO)
    
    tuner = MLPlaybookTuner()
    
    try:
        # Generate recommendations
        session = tuner.generate_tuning_recommendations(lookback_days=30)
        
        print(f"\n🧠 ML Tuning Session: {session.session_id}")
        print(f"📊 Analyzed {session.total_trades_analyzed} trades")
        print(f"🎯 Data Quality Score: {session.data_quality_score}")
        print(f"💡 Generated {len(session.recommendations)} recommendations")
        
        for rec in session.recommendations:
            print(f"\n📈 {rec.regime.upper()} - {rec.parameter}")
            print(f"   Current: {rec.current_value}")
            print(f"   Recommended: {rec.recommended_value}")
            print(f"   Confidence: {rec.confidence:.1%}")
            print(f"   Risk: {rec.risk_level}")
            print(f"   Reasoning: {rec.reasoning}")
        
    except Exception as e:
        print(f"Error: {e}")
