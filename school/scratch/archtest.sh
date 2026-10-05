#!/usr/bin/env bash
cd ~/eva-olmo/school
export HF_HOME=~/eva-olmo/hf-home PYTHONDONTWRITEBYTECODE=1
PY=~/eva-olmo/.venv-train/bin/python
CONV=/opt/llama/src/llama.cpp/convert_hf_to_gguf.py
$PY archtest.py archtest gutenberg/sample.txt || exit 1
for m in llama-gpt2tok gpt2-gpt2tok llama-ownbpe llama-ownspm; do
  echo "=== $m convert"
  $PY $CONV archtest/$m --outtype f16 --outfile archtest/$m.gguf > archtest/$m.convert.log 2>&1
  echo "convert exit $?"
  grep -E "ERROR|Error|rror:|NotImplemented|not recognized|chkhsh|Model successfully" archtest/$m.convert.log | tail -6
  if [ -f archtest/$m.gguf ]; then
    echo "=== $m run"
    timeout 60 ~/eva-olmo/build/bin/llama-completion -m archtest/$m.gguf -ngl 0 -dev none -c 256 -p "The house did not answer" -n 8 --temp 1 --seed 1 -no-cnv --simple-io > archtest/$m.run.log 2>&1 < /dev/null
    echo "run exit $?"
    grep -E "add_bos|BOS|error|failed|eval time|tokenizer.ggml.pre|general.architecture" archtest/$m.run.log | head -8
  fi
done
echo ARCHTEST-DONE
