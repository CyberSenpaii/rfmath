# rfmath.py
usage: ```rfmath [-h] {power,gain,eirp,link-budget}``` 
# Examples
```python rfmath.py power 10W```
```python rfmath.py gain 20dBm +3dB -2dB```
```python rfmath.py eirp --tx 20dBm --gain 6dBi --loss 2dB```
```python rfmath.py link-budget --tx 20dBm --tx-gain 6dBi --tx-loss 2dB --freq 2400MHz --distance 1km --rx-gain 6dBi --rx-loss 2dB --rx-sensitivity=-80dBm```
