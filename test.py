
try:
    from utils.map_viewer import MapViewer
    print('SUCCESS: MapViewer imported successfully')
    print(f'MapViewer class: {MapViewer}')
except Exception as e:
    print(f'ERROR: {type(e).__name__}: {e}')
    import traceback
    traceback.print_exc()
