import json
import os
import shutil
import sys

import sentencepiece as spm
import torch
from tokenizers import Tokenizer, decoders, models, pre_tokenizers, trainers
from transformers import AutoTokenizer, GPT2Config, GPT2LMHeadModel, LlamaConfig, LlamaForCausalLM, PreTrainedTokenizerFast

root = sys.argv[1]
sample = sys.argv[2]
os.makedirs(root, exist_ok=True)
torch.manual_seed(0)


def llama(vocab, bos, eos):
    return LlamaForCausalLM(LlamaConfig(vocab_size=vocab, hidden_size=128, intermediate_size=384, num_hidden_layers=2, num_attention_heads=4, num_key_value_heads=4, max_position_embeddings=1024, bos_token_id=bos, eos_token_id=eos, tie_word_embeddings=True))


def gpt2(vocab, bos, eos):
    return GPT2LMHeadModel(GPT2Config(vocab_size=vocab, n_embd=128, n_layer=2, n_head=4, n_positions=1024, bos_token_id=bos, eos_token_id=eos))


def save(name, model, tok_saver):
    d = os.path.join(root, name)
    shutil.rmtree(d, ignore_errors=True)
    model.to(torch.bfloat16).save_pretrained(d)
    tok_saver(d)
    print("built", d)


gtok = AutoTokenizer.from_pretrained("openai-community/gpt2")
save("llama-gpt2tok", llama(50304, gtok.eos_token_id, gtok.eos_token_id), gtok.save_pretrained)
save("gpt2-gpt2tok", gpt2(50304, gtok.eos_token_id, gtok.eos_token_id), gtok.save_pretrained)

bpe = Tokenizer(models.BPE())
bpe.pre_tokenizer = pre_tokenizers.ByteLevel(add_prefix_space=False)
bpe.decoder = decoders.ByteLevel()
bpe.train([sample], trainers.BpeTrainer(vocab_size=8192, special_tokens=["<|endoftext|>"], initial_alphabet=pre_tokenizers.ByteLevel.alphabet()))
own = PreTrainedTokenizerFast(tokenizer_object=bpe, bos_token="<|endoftext|>", eos_token="<|endoftext|>")
save("llama-ownbpe", llama(8192, 0, 0), own.save_pretrained)

spm.SentencePieceTrainer.train(input=sample, model_prefix=os.path.join(root, "spm8k"), vocab_size=8192, model_type="bpe", byte_fallback=True, character_coverage=1.0, bos_id=1, eos_id=2, unk_id=0, pad_id=-1, normalization_rule_name="identity", split_digits=True, allow_whitespace_only_pieces=True, remove_extra_whitespaces=False)


def spm_saver(d):
    shutil.copy(os.path.join(root, "spm8k.model"), os.path.join(d, "tokenizer.model"))
    with open(os.path.join(d, "tokenizer_config.json"), "w") as f:
        json.dump({"add_bos_token": True, "add_eos_token": False, "bos_token": "<s>", "eos_token": "</s>", "unk_token": "<unk>", "tokenizer_class": "LlamaTokenizer"}, f)


save("llama-ownspm", llama(8192, 1, 2), spm_saver)
